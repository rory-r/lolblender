# ##### BEGIN GPL LICENSE BLOCK ##### #
# lolblender - Python addon to use League of Legends files into blender
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of  MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####

# Animation-specific changes are based on the work in "LOLViewer" under GPLv3
# (Copyright 2011-2012 James Lammlein, Adrian Astley),
# and the previous work in this project by Zac Berkowitz on "lolBlender"
# with adaption done by Pascal Lis (github -> lispascal)
#
# Version 4 .anm files are in LOLViewer with the following info: 
# "Based on the reverse engineering work of Hossein Ahmadi."
# and this file makes use of that work

# <pep8 compliant>
import struct
import mathutils

class anmHeader():
    """LoL animation header format:
    id                  char[8]     8       
    version             uint        4       Version number.

    v1
        magic               char[12]     12       "magic"
        numBones            uint        4
        offset?             uint        4
        numFrames           uint        4
        unknown             uint        4       leona_joke_60fps is 10.6333, taunt is 6.9333
                                                perhaps this is time per frame
        playbackFPS         float       4
        2                   float       4
        10                  float       4
        2                   float       4
        10                  float       4
        0.01                float       4
        0.2                 float       4
        more?               ?           ?

    v0,2-3
        magic               uint        4       "magic" number
        numBones            uint        4       Number of bones
        numFrames           uint        4       Number of frames
        playbackFPS         uint        4       FPS of playback

    v4
        magic               uint        4       "magic" number
        unknown             float[3]    12
        numBones            uint        4       Number of bones
        numFrames           uint        4       Number of frames
        timePerFrame        float       4       1/fps
        offsets             uint[3]     12      offsets
        positionOffset      uint        4
        orientationOffset   uint        4
        indexOffset         uint        4
        offsets2            uint[3]     12      ?


    
    total size v0,2-3                   28 bytes
    total size v1                       68+ bytes
    total size v4                       76 bytes

    """

    def __init__(self):
        self.__format__i = '<8si'  # initial part
        self.__size__i = struct.calcsize(self.__format__i)
        self.__format__v1 = '<12s4i7f'  # part for version 1
        self.__size__v1 = struct.calcsize(self.__format__v1)
        self.__format__v023 = '<4i'  # part for version 0-3
        self.__size__v023 = struct.calcsize(self.__format__v023)
        self.__format__v4 = '<i3f2if9i'  # part for version 4
        self.__size__v4 = struct.calcsize(self.__format__v4)
        self.id = None
        self.version = None
        self.magic = None
        self.numBones = None
        self.numFrames = None
        self.playbackFPS = None

    def fromFile(self, anmFile):
        """Reads the skl header object from the raw binary file"""
        anmFile.seek(0)
        beginning = struct.unpack(self.__format__i, anmFile.read(self.__size__i))
        (self.id, self.version) = beginning

        print("ANM Version: %d" % self.version)
        if self.version in [0, 2, 3]:  # versions 0-3
            rest = struct.unpack(self.__format__v023, anmFile.read(self.__size__v023))
            (self.magic, self.numBones, self.numFrames, self.playbackFPS) = rest
            print("anmMagic: %s" % self.magic)
            print("anmNumBones: %s" % self.numBones)
            print("anmnumFrames: %s" % self.numFrames)
            print("anmplaybackFPS: %s" % self.playbackFPS)
        elif self.version == 1:  # version 1
            rest = struct.unpack(self.__format__v1, anmFile.read(self.__size__v1))
            (self.magic, self.numBones, self.offset, self.numFrames, 
                    self.unknown, self.playbackFPS) = rest[0:6]
            if (rest[6] != 2 or rest[7] != 10 or rest[8] != 2 or rest[9] != 10 or 
                    rest[10] != .01 or rest[11] != 0.2):
                print("ANM file headers unexpected values: ")
                print(rest[6:12])
            raise ValueError("Version %s ANM not supported" % self.version)
        elif self.version == 4:  # version 4
            rest = struct.unpack(self.__format__v4, anmFile.read(self.__size__v4))
            self.magic = rest[0]
            self.unknown = rest[1:4]
            self.numBones = rest[4]
            self.numFrames = rest[5]
            timePerFrame = rest[6]
            self.playbackFPS = round(1.0 / timePerFrame)
            self.offsets = rest[7:10]
            self.positionOffset = rest[10]
            self.orientationOffset = rest[11]
            self.indexOffset = rest[12]
            self.offsets2 = rest[13:16]
        else:
            raise ValueError("Version %s ANM not supported" % self.version)
        print("Version: %s" % self.version)
        print("magic: %s" % self.magic)
    
    def toFile(self, anmFile):
        """Writes the header object to a raw binary file"""
        data = struct.pack(self.__format__i, self.id, self.version)
        anmFile.write(data)
        
        if self.version in [0,2,3]:
            data = struct.pack(self.__format__v023, self.magic, self.numBones, self.numFrames, self.playbackFPS)
            anmFile.write(data)


class anmBone():
    """LoL Bone structure format
    v0,2-3
    name        char[32]    32      name of bone (with padding \0's)
    unknown     int         4       

    frame[numberOfFrames]:
        orientation     float[4]    16
        position        float[3]    12

    total                   36 + (28 * Number of Frames)

    v1,4
    Animation information is separated by frame for version 4 and probably v1
    """
    def __init__(self):
        self.__format__i = '<32si'  # initial
        self.__size__i = struct.calcsize(self.__format__i)
        self.__format__f = '<7f'  # per frame
        self.__size__f = struct.calcsize(self.__format__f)
        self.name = None
        self.parent = None
        self.orientations = []
        self.positions = []


    def metaDataFromFile(self, anmFile, version):
        """Reads animation bone meta-data from a binary file fid"""
        if version in [0,2,3]:
            fields = struct.unpack(self.__format__i, 
                    anmFile.read(self.__size__i))
            # for e in ['utf-8', 'utf-16', 'ascii', 'latin-1', 'iso-8859-1',
            #         'gb2312', 'Windows-1251', 'windows-1252']:
            #     try:
            #         name = bytes.decode(fields[0], e)
            #         print("%s: %s" % (e, name) )
            #     except UnicodeDecodeError:
            #         print("%s failed" % e)
            #         pass
            name = bytes.decode(fields[0])

            self.name = name.rstrip('\0')
            self.unknown = fields[1]

        else:
            raise ValueError("Unhandled Bone version number", version)

    def frameDataFromFile(self, anmFile, version):
        """Reads animation bone frame data from a binary file fid"""
        if version in [0,2,3]:
            fields = struct.unpack(self.__format__f,
                    anmFile.read(self.__size__f))
            orientation = mathutils.Quaternion([-fields[3], fields[0],
                    fields[1], -fields[2]])
            # orientation = mathutils.Quaternion(fields[0:4])
            position = mathutils.Vector(fields[4:7])
            position.z *= -1
            self.add_frame(position, orientation)
        else:
            raise ValueError("Unhandled Bone version number", version)

    def add_frame(self, position, orientation):
        """Adds a position Vector and orientation Quaternion to this bone's
        lists, representing a new frame."""
        self.positions.append(position)
        self.orientations.append(orientation)

    def get_frame(self, frame_number):
        """Returns the position Vector and orientation Quaternion of a bone
        in a given frame."""
        return self.positions[frame_number], self.orientations[frame_number]

    def toFile(self, anmFile, version):
        """Writes animation bone object to a binary file FID"""
        if version in [0,2,3]:
            data = struct.pack(self.__format__i, self.name.encode(), self.unknown)
            for j in range(0, len(self.orientations)):
                data += struct.pack(self.__format__f, self.orientations[j][1], self.orientations[j][2], -self.orientations[j][3], -self.orientations[j][0], self.positions[j][0], self.positions[j][1], self.positions[j][2])
            anmFile.write(data)


def importANM(filepath):
    header = anmHeader()
    boneList= []
    
    #Wrap open in try block
    anmFid = open(filepath, 'rb')

    #Read the file header to get # of bones
    header.fromFile(anmFid)
    if header.version in [0, 1, 2, 3]:
        #Read in the bones
        for i in range(header.numBones):
            boneList.append(anmBone())
            boneList[i].metaDataFromFile(anmFid, header.version)
            # print("bone %s: %s" % (i, boneList[i].name))
            for j in range(header.numFrames):
                # print(j)
                boneList[i].frameDataFromFile(anmFid, header.version)
            # print("p:%s\no:%s" % (boneList[i].positions[0],
            #             boneList[i].orientations[0]))

    elif header.version == 4:
        print("not supported yet")
    else:
        raise ValueError("ANM File Version not supported.", header.version)


    anmFid.close()
    return header, boneList


def applyANM(header, boneList):
    import bpy
    
    # http://blender.stackexchange.com/a/8392
    # http://blender.stackexchange.com/a/31709

    try:
        bpy.ops.objects['lolArmature'].mode_set(mode='EDIT')
        print("TEST")
    except:
        pass

    scene = bpy.context.scene
    ob = bpy.context.scene.objects['lolArmature']
    editBones = ob.data.edit_bones
    poseBones = ob.pose.bones

    parentOffset = {}
    parentOffRot = {}
    
    for editBone in editBones:
        if editBone.parent != None:
            # get offset from parent bone in bone's object space
            parentOffset[editBone.name] = mathutils.Vector(editBone.head - editBone.parent.head) @ editBone.matrix
            # get bone rotation relative to the parent bone
            parentOffRot[editBone.name] = editBone.parent.matrix.to_quaternion().rotation_difference(editBone.matrix.to_quaternion())
        else:
            parentOffset[editBone.name] = mathutils.Vector(editBone.head) @ editBone.matrix
            parentOffRot[editBone.name] = mathutils.Quaternion([1.0, 0.0, 0.0, 0.0]).rotation_difference(editBone.matrix.to_quaternion())

    if header.version in [1, 3, 4, 5]:
        scene.render.fps = header.playbackFPS
        scene.frame_end = header.numFrames - 1
        scene.frame_start = 0
        for f in range(header.numFrames):
            print("frame %s processing" % f)
            scene.frame_set(f)
            
            for b in boneList:
                n = b.name
                boneRotation = b.orientations[f]
                bonePosition = b.positions[f]

                poseBone = poseBones[n]
                editBone = editBones[n]
                
                if poseBone.parent:
                    # bonePosition is in parent bone's object space so convert to absolute position
                    bonePosition = bonePosition @ poseBone.parent.matrix.inverted()
                
                # convert absolute position to position in bone's object space
                bonePosition = bonePosition @ editBone.matrix
                
                poseBone.rotation_quaternion = parentOffRot[n].inverted() @ boneRotation
                poseBone.location = bonePosition - parentOffset[n]

                for dp in ["rotation_quaternion", "location"]:
                    poseBone.keyframe_insert(data_path=dp, frame=f)
            # ob.keyframe_insert(data_path="pose")
                

    elif header.version == 4:
        raise NotImplementedError("version 4 not supported yet")
    else:
        raise ValueError("Version not supported", header.version)
    # Once implemented, this code will probably follow a relatively simply
    # structure to bone creation. Althought it will be:
    # go by frame->insert key frame



def exportANM(skelObj, output_filepath, input_filepath, OVERWRITE_FILE_VERSION, VERSION):
    import bpy
    
    (import_header, import_bonelist) = importANM(input_filepath)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    skelObj.select = True
    bpy.ops.object.mode_set(mode='EDIT')
    
    scene = bpy.context.scene
    objBones = skelObj.data.bones
    pb = skelObj.pose.bones
    numBones = len(objBones)
    
    header = import_header
    if OVERWRITE_FILE_VERSION:
        header.version = VERSION
        
        #Apply changes to the header based on the new version here
    
    if header.version in [0,2,3]:
        header.numBones = numBones
        header.numFrames = scene.frame_end - scene.frame_start + 1
        
        boneList = []
        parentOffset = {}
        parentOffRot = {}
        
        for i, b in enumerate(objBones):
            boneList.append(anmBone())
            boneList[-1].name = b.name
            
            #most bones have a value of zero / bones without parent have a value of 2 / 
            if b.parent != None:
                boneList[-1].unknown = 0
                
                parentOffset[b.name] = mathutils.Vector(b.matrix_local.decompose()[0] - b.parent.matrix_local.decompose()[0]) @ b.matrix_local
                parentOffRot[b.name] = objBones[b.parent.name].matrix_local.to_quaternion().rotation_difference(b.matrix_local.to_quaternion())
            else:
                boneList[-1].unknown = 2
                
                parentOffset[b.name] = mathutils.Vector(b.head) @ b.matrix_local
                parentOffRot[b.name] = mathutils.Quaternion([1.0, 0.0, 0.0, 0.0])
        
        for f in range(scene.frame_start, scene.frame_end + 1):
            bpy.context.scene.frame_set(f)
            
            for b in boneList:
                n = b.name
                objBone = objBones[n]
                poseBone = pb[n]
                bonePos = poseBone.location
                
                bonePos = bonePos + parentOffset[n]
                boneOrient = parentOffRot[n] @ poseBone.rotation_quaternion
                
                if objBone.parent != None:
                    bonePos = bonePos @ objBone.matrix_local.inverted()
                    bonePos = bonePos @ poseBone.parent.matrix
                
                bonePos[2] = -bonePos[2]
                
                b.add_frame(bonePos, boneOrient)
        
        anmFid = open(output_filepath, 'wb')
        
        header.toFile(anmFid)
        
        for b in boneList:
            b.toFile(anmFid, import_header.version)
        
        anmFid.close()
        
    else:
        raise ValueError("Version %d not supported!" % header.version)