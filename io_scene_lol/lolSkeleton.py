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

# <pep8 compliant>
import struct
import mathutils

class sklHeader():
    """LoL skeleton header format:
v1-2
    fileType        char[8]     8       id string
    version      int            4       possibly number of objects (1-2), 0 is different version
    skeletonHash    int         4       unique id number?
    numBones        int         4       number of bones

    total size                  20 Bytes

v0
    fileType        char[8]     8       id string
    version         int         4       version # (0)
    zero            short       2       ?
    numBones        short       2       
    numBoneIDs      int         4
    offsetVertexData    short   2       usually 64
    unknown         short       2       if 0, maybe this and above are one int

    offset1         int         4       ?
    offsetToAnimationIndices    4       
    offset2         int         4       ?
    offset3         int         4       ?
    offsetToStrings int         4    
    empty                       20

    total size                  64 Bytes          

    """

    def __init__(self):
        self.__format__i = '<8si'
        self.__format__v12 = '<2i'
        self.__format__v0 = '<2hi2h5i'
        self.__size__i = struct.calcsize(self.__format__i)
        self.__size__v12 = struct.calcsize(self.__format__v12)
        self.__size__v0 = struct.calcsize(self.__format__v0)
        self.fileType = None
        self.version = None
        self.skeletonHash = None
        self.numBones = None

    def fromFile(self, sklFile):
        """Reads the skl header object from the raw binary file"""
        sklFile.seek(0)
        beginning = struct.unpack(self.__format__i, sklFile.read(self.__size__i))
        (fileType, self.version) = beginning
        if self.version in [1, 2]:  # 1 or 2
            rest = struct.unpack(self.__format__v12, sklFile.read(self.__size__v12))
            (self.skeletonHash, self.numBones) = rest
        elif self.version == 0:  # version 0
            rest = struct.unpack(self.__format__v0, sklFile.read(self.__size__v0))
            (self.zero, self.numBones, self.numBoneIDs, self.offsetVertexData,
                    self.unknown, self.offset1, self.offsetAnimationIndices,
                    self.offset2, self.offset3, self.offsetToStrings) = rest
            sklFile.seek(self.offsetVertexData)
        # fields = struct.unpack(self.__format__, sklFile.read(self.__size__))
        # (fileType, self.version, 
        #         self.skeletonHash, self.numBones) = fields

        # self.fileType = bytes.decode(fileType)
        self.fileType = fileType

    
    def toFile(self, sklFile):
        """Writes the header object to a raw binary file"""
        data = struct.pack(self.__format__i, self.fileType, self.version)
        
        if self.version in [1,2]:
            data += struct.pack(self.__format__v12, self.skeletonHash, self.numBones)
        sklFile.write(data)


class sklBone():
    """LoL Bone structure format
    v1-2
    name        char[32]    32      name of bone
    parent      int         4       id # of parent bone. Root bone = -1
    scale       float       4       scale
    matrix      float[3][4] 48      affine bone matrix
                                    [x1 x2 x3 xt
                                     y1 y2 y3 yt
                                     z1 z2 z3 zt]
    total                   88
    
    v0  (thanks to LolViewer makers)
    zero        short       2       ?
    id          short       2       
    parent      short       2       
    unknown     short       2       ? combined with above gives int?
    "namehash"  int         4       
    twopointone float       4       the value 2.1 as a float. 
                                    maybe a scaling, 2.1 value for most .skls
    position    float[3]    12      position of bone
    scaling?    float[3]    12      possibly scaling in x-y-z. values of 1
    orientation float[4]    16      quaternion of orientation
    ct          float[3]    12      "ctx, cty, ctz", probably another position
                                    ("translation")
    padding?    byte[32]    32      

    total                   100
    """
    def __init__(self):
        self.__format__v12 = '<32sif12f'
        self.__size__v12 = struct.calcsize(self.__format__v12)
        self.__format__v0 = '<4hi22f'
        self.__size__v0 = struct.calcsize(self.__format__v0)
        self.name = None
        self.parent = None
        self.scale = None
        self.matrix = [[],[],[]]


    def fromFile(self,sklFile, version):
        """Reads skeleton bone object from a binary file fid"""
        if version in [1,2]:
            fields = struct.unpack(self.__format__v12, 
                    sklFile.read(self.__size__v12))
            self.name = bytes.decode(fields[0]).rstrip('\0')
            self.parent, self.scale = fields[1:3]
            #Strip null \x00's from the name

            #make z negative
            self.matrix[0] = list( fields[3:7] )
            self.matrix[1] = list( fields[7:11] )
            self.matrix[2] = list( fields[11:15] )

            #Flip z axis
            for k in range(4):
                self.matrix[2][k] = -self.matrix[2][k]
        elif version == 0:
            fields = struct.unpack(self.__format__v0,
                    sklFile.read(self.__size__v0))
            self.id = fields[1]
            self.parent = fields[2]
            self.name = fields[4]
            twopointone = fields[5]
            self.position = list(fields[6:9])
            self.position[2] *= -1. # make z negative
            self.scale = fields[9:12]
            self.quat = mathutils.Quaternion([
                    - fields[15], fields[12], fields[13],
                    - fields[14]])
            # self.matrix = self.quat.to_matrix()
            # self.matrix2 = [[],[],[],[]]
            # for i in range(0,3):
            #     self.matrix2[i] = [self.matrix[i][0], self.matrix[i][1], 
            #             self.matrix[i][2], self.position[0]]
            # self.matrix2[3] = [0, 0, 0, 1]
            # print(self.matrix)
            self.ct = list(fields[16:19])
            for i in [1,2]:
                self.ct[i] *= -1.
            self.extra = list(fields[19:27])
            # print("q%s" % self.quat)
            # print("m%s" % self.matrix)
            # print("p%s" % self.position)
            # print("c%s" % self.ct)
            # sklFile.seek(sklFile.tell()+32)  # skip 32 padding bytes

        else:
            raise ValueError('unhandled version number', version)

    def toFile(self,sklFile):
        """Writes skeleton bone object to a binary file FID"""

        data = struct.pack('<32sif', self.name.encode(), self.parent, self.scale)
        for j in range(3):
            for k in range(4):
                data += struct.pack('<f', self.matrix[j][k]) 

        sklFile.write(data)

    def copy(self):
        newBone = sklBone()
        newBone.name = self.name
        newBone.parent = self.parent
        newBone.scale = self.scale
        newBone.matrix = self.matrix
        try:
            newBone.quat = self.quat
        except:
            pass
        return newBone


def importSKL(filepath):
    header = sklHeader()
    boneList= []
    reorderedBoneList = []
    
    #Wrap open in try block
    sklFid = open(filepath, 'rb')
    print("Reading SKL: %s" % filepath)
    #Read the file header to get # of bones
    header.fromFile(sklFid)
    print("SKL version:%s" % header.version)
    if header.version in [1, 2]:
        #Read in the bones
        for k in range(header.numBones):
            boneList.append(sklBone())
            boneList[k].fromFile(sklFid, header.version)
        


        if header.version == 2:  # version 2 has a reordered bone list
            #Read in reordered bone assignments
            numBoneIDs = struct.unpack('<i', sklFid.read(4))[0]  # clue taken from LolViewer
            print ("reordered list size: %i" % numBoneIDs)
            for i in range(0, numBoneIDs):
                buf = sklFid.read(4)
                if buf == b'':
                    break
                else:
                    boneId = struct.unpack('<i', buf)[0]
                reorderedBoneList.append(boneList[boneId].copy())
            
    elif header.version == 0:
        # taken from c# code from LoLViewer
        for k in range(header.numBones):
            boneList.append(sklBone())
            boneList[k].fromFile(sklFid, header.version)
        print("(off1) from %s to %s" % (sklFid.tell(), header.offset1))
        sklFid.seek(header.offset1)
        # indices for version 4 animation
        header.boneIDMap = {}
        for i in range(0, header.numBones):
            # 8 bytes
            sklID, anmID = struct.unpack('<2i', sklFid.read(
                    struct.calcsize('<2i')))
            header.boneIDMap[anmID] = sklID


        print("(offstr) from %s to %s" % (sklFid.tell(), header.offsetToStrings))
        sklFid.seek(header.offsetToStrings)
        for i in range(0, header.numBones):
            name = []
            while name.count(b'\0') == 0:
                for j in range(0,4):
                    name.append(sklFid.read(1))
            end = name.index(b'\0')
            boneList[i].name = ''.join(
                    v.decode() for v in name[0:end])
            DEBUG_PRINT = False
            if DEBUG_PRINT and boneList[i].name.lower() in ['root', 'r_weapon', 'shield',
                    'l_shield', 'r_shield', 'buffbone_cstm_shield_top',
                    'buffbone_glb_weapon_1', 'l_hip']:
                bone = boneList[i]
                print("%s:" % bone.name)
                print("p:%s" % bone.position)
                print("ct:%s" % bone.ct)
                print("q:%s" % bone.quat)
                if bone.parent > -1:
                    tct = mathutils.Vector(bone.ct)
                    tct.rotate(boneList[bone.parent].quat)
                    print("tct:%s" % tct)

                print("Mags: p:%f, ct:%f" % (mathutils.Vector(
                        bone.position).length, mathutils.Vector(
                        bone.ct).length))
                # print("ex:%s" % boneList[i].extra)

        # below is technically earlier in file than above
        print("(offani) from %s to %s" % (sklFid.tell(), header.offsetAnimationIndices))
        sklFid.seek(header.offsetAnimationIndices)
        for i in range(0, header.numBoneIDs):
            boneId = struct.unpack('<h', sklFid.read(
                    struct.calcsize('<h')))[0]
            reorderedBoneList.append(boneList[boneId].copy())
        print("end: %s" % sklFid.tell())
    else:
        raise ValueError("Version %i not supported" % header.version)

    sklFid.close()
    return header, boneList, reorderedBoneList



def buildSKL(boneList, version):
    import bpy
    import math
    import mathutils
    
    #Create Blender Armature
    bpy.ops.object.armature_add(location=(0,0,0), enter_editmode=True)
    obj = bpy.context.active_object
    arm = obj.data

    bones = arm.edit_bones
    #Remove the default bone
    bones.remove(bones[0])
    #import the bones

    print(len(boneList))
    # print("%s, p:%s" % (boneName, boneList[bone.parent].name if bone.parent > -1 else None))

    if version in [1,2]:
        for boneID, bone in enumerate(boneList):
            boneName = bone.name.rstrip('\x00')
            newBone = arm.edit_bones.new(boneName)
            
            boneMatrix = mathutils.Matrix()
            for x in range(4):
                for y in range(3):
                    boneMatrix[y][x] = bone.matrix[y][x]
            
            newBone.head = (bone.matrix[0][3], bone.matrix[1][3], bone.matrix[2][3])
            
            #rotVector is the y-Axis of the bone
            rotVector = mathutils.Vector((bone.matrix[0][1], bone.matrix[1][1], bone.matrix[2][1]))
            newBone.tail = newBone.head + rotVector * 3
            
            #calculate the roll of the bone based on the x-Vector the bone has before the roll is applied
            #and the x-Vector it should have after applying it
            newRollVec = mathutils.Vector([bone.matrix[0][0], bone.matrix[1][0], bone.matrix[2][0]])
            oldRollVec = mathutils.Vector([newBone.matrix[0][0], newBone.matrix[1][0], newBone.matrix[2][0]])
            normal = mathutils.Vector((bone.matrix[0][1], bone.matrix[1][1], bone.matrix[2][1]))
            
            #https://stackoverflow.com/questions/5188561/signed-angle-between-two-3d-vectors-with-same-origin-within-the-same-plane
            roll = math.atan2(oldRollVec.cross(newRollVec) @ normal, oldRollVec @ newRollVec)
            
            newBone.roll = roll
            
            boneParentID = bone.parent
            
            if boneParentID > -1:
                boneParentName = boneList[boneParentID].name
                parentBone = arm.edit_bones[boneParentName]
                newBone.parent = parentBone

    elif version == 0:

        for boneID, bone in enumerate(boneList):
            #algorithm here based off of above, and LolViewer code
            #If this bone is a child, find the parent's tail and attach this bone's
            #head to it
            parentPos = mathutils.Vector([0,0,0])
            boneHead = mathutils.Vector(bone.position)

            boneParentID = bone.parent
            boneName = bone.name.rstrip('\x00')
            # debug
            # if boneName.count("weapon"):
            #     print("prev: %s" % boneList[boneID-1].name)
            #     print("%s, id:%s\np:%s\nq:%s\ns:%s" % (bone.name, boneID, bone.position, bone.quat, bone.scale))
            #     print("c%s" % bone.ct)
            #     # print("E%s" % bone.extra)
            newBone = arm.edit_bones.new(boneName)
            if boneParentID > -1:
                boneParentName = boneList[boneParentID].name
                parentBone = arm.edit_bones[boneParentName]

                newBone.parent = parentBone
                parQuat = boneList[boneParentID].quat
                boneHead.rotate(parQuat)  # only apply parent rotation to self
                bone.quat = parQuat @ bone.quat  # for children

                # parentPos = mathutils.Vector(boneList[boneParentID].position)
                parentPos = parentBone.head
            newBone.head = parentPos + boneHead
            boneMatrix = bone.quat.to_matrix()
            newBone.tail = newBone.head + mathutils.Vector([boneMatrix[0][1],boneMatrix[1][1],boneMatrix[2][1]])
            
            newRollVec = mathutils.Vector([boneMatrix[0][0], boneMatrix[1][0], boneMatrix[2][0]])
            oldRollVec = mathutils.Vector([newBone.matrix[0][0], newBone.matrix[1][0], newBone.matrix[2][0]])
            normal = mathutils.Vector((boneMatrix[0][1], boneMatrix[1][1], boneMatrix[2][1]))
            #https://stackoverflow.com/questions/5188561/signed-angle-between-two-3d-vectors-with-same-origin-within-the-same-plane
            roll = math.atan2(oldRollVec.cross(newRollVec) @ normal, oldRollVec @ newRollVec)
            
            newBone.roll = roll

        # set bones with children to be average of the
        # for boneID, bone in enumerate(boneList):
        #     numChildren = len(children[boneID]['all'])
        #     if numChildren > 0:
        #         pos = mathutils.Vector([0,0,0])
        #         for b in children[boneID]['all']:
        #             pos += arm.edit_bones[b].head/numChildren
        #         arm.edit_bones[bone.name].tail = pos

    bpy.ops.object.mode_set(mode='OBJECT')


def exportSKL(meshObj, skelObj, output_filepath, input_filepath):
    import bpy
    
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    skelObj.select = True
    
    objBones = skelObj.data.bones
    numBones = len(objBones)
    bones = []
    
    for b in objBones:
        bones.append(sklBone())
        bones[-1].name = b.name
        if b.parent != None:
            for boneId, bone in enumerate(objBones):
                if b.parent == bone:
                    bones[-1].parent = boneId
                    break
        else:
            bones[-1].parent = -1
        bones[-1].scale = 0.1 #this value is always 0.1 ?
        bones[-1].matrix = b.matrix_local
        
        for k in range(3):
            bones[-1].matrix[k][2] = -bones[-1].matrix[k][2]
        for k in range(4):
            bones[-1].matrix[2][k] = -bones[-1].matrix[2][k]
    
    
    (import_header, import_boneList, import_reorderedBoneList) = importSKL(input_filepath)
    
    header = import_header
    
    header.numBones = numBones
    
    if header.version in [1,2]:
        numReorderedBones = len(meshObj.vertex_groups)
        reorderedBoneList = []
        
        for g in meshObj.vertex_groups:
            groupName = g.name
            for boneIndex, bone in enumerate(objBones):
                if bone == objBones[groupName]:
                    index = boneIndex
                    break
            
            reorderedBoneList.append(index)
    else:
        raise ValueError("Version %d not supported!" % header.version)
    
    sklFid = open(output_filepath, 'wb')
    
    header.toFile(sklFid)
    
    for b in bones:
        b.toFile(sklFid)
    
    sklFid.write(struct.pack('<1i', numReorderedBones))
    
    for b in reorderedBoneList:
        sklFid.write(struct.pack('<1i', b))
    
    sklFid.close()