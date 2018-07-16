import math
import bpy
import mathutils
import bmesh
from mathutils import Vector
from bpy.types import Operator, PropertyGroup, Object, Panel
from bpy.props import StringProperty, FloatProperty, BoolProperty, IntProperty

class BuildingMakerPanel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_context = "objectmode"
    bl_category = "Create"
    bl_label = "Add Building"

    def draw(self, context):
        TheCol = self.layout.column(align=True)
        self.layout.prop(bpy.context.scene.building_props, 'size_x_prop')
        self.layout.prop(bpy.context.scene.building_props, 'size_y_prop')
        self.layout.prop(bpy.context.scene.building_props, 'level_count_prop')
        self.layout.prop(bpy.context.scene.building_props, 'level_height_prop')
        self.layout.prop(bpy.context.scene.building_props, 'wnd_width_prop')
        self.layout.prop(bpy.context.scene.building_props, 'wnd_height_prop')
        self.layout.prop(bpy.context.scene.building_props, 'interval_width_prop')
        self.layout.prop(bpy.context.scene.building_props, 'gap_prop')
        self.layout.prop(bpy.context.scene.building_props, 'top_gap_prop')
        self.layout.prop(bpy.context.scene.building_props, 'bottom_gap_prop')

        TheCol.operator("mesh.make_building", text="Add Building")
    #end draw

#end BuildingMakerPanel

# ------------------------------------------------------------------
# Define property group class to create or modify
# ------------------------------------------------------------------
class MakerPanelProperties(PropertyGroup):
    size_x_prop = IntProperty(
            name='X Size', min=1, default=30,
            description='X Size of building, meters',
            )
    size_y_prop = IntProperty(
            name='Y Size', min=1, default=10,
            description='Y Size of building, meters',
            )
    level_count_prop = IntProperty(
            name='Level count', min=1, default=3,
            description='Building levels count',
            )
    level_height_prop = FloatProperty(
            name='Level height', min=1, default=3,
            description='Building level height, meters',
            )
    wnd_width_prop = FloatProperty(
            name='Window width', min=0.1, default=1.46,
            description='Window width, meters',
            )
    wnd_height_prop = FloatProperty(
            name='Window height', min=0.1, default=1.46,
            description='Window height, meters',
            )
    interval_width_prop = FloatProperty(
            name='Interval width', min=0.1, default=1.5,
            description='Horizontal interval width, meters',
            )
    gap_prop = FloatProperty(
            name='Min horiz gap', min=0.1, default=3,
            description='Min left/right gap size , meters',
            )
    top_gap_prop = FloatProperty(
            name='Top gap', min=0.1, default=1,
            description='Top gap size , meters',
            )
    bottom_gap_prop = FloatProperty(
            name='Bottom gap', min=0.1, default=2.5,
            description='Bottom gap size , meters',
            )


class MakeBuilding(bpy.types.Operator) :
    bl_idname = "mesh.make_building"
    bl_label = "Building"
    bl_options = {"REGISTER", "UNDO"}     
    
    def draw(self, context) :
        TheCol = self.layout.column(align = True)
        #TheCol.prop(self, "inverted")
    #end draw
    
    def generate_stripe(self, vectors, faces, cols, i, size, x,y,z):
        for j,w in enumerate(cols):
                vectors.append(Vector((x,y,z)))
                x += w
                if i > 0 and j > 0: 
                    faces.append([(i-1)*size + j - 1, (i-1)*size + j, i*size + j, i*size + j - 1])
            
        vectors.append(Vector((x,y,z)))
        if i > 0: 
            faces.append([(i-1)*size + size - 2, (i-1)*size + size - 1, i*size + size - 1, i*size + size - 2])
    #end generate_stripe
    
    def generate_wall_segs(self, length, wnd_width, interval_width, min_gap): 
        cnt = int((length - (wnd_width + min_gap * 2)) / (wnd_width + interval_width))
    
        real_gap = (1.0 * length - (wnd_width + interval_width) * cnt - wnd_width) / 2;
        
        cols = []
        cols.append(real_gap)
        for i in range(cnt):
            cols.append(wnd_width)
            cols.append(interval_width)
        cols.append(wnd_width)
        cols.append(real_gap)
        return cols
    
    def generate_height_segs(self, levels, level_height, bottom_gap, wnd_height, top_gap):
        height_segs = []
        total_ht = 0
        for i in range(levels):
            if i == 0:
                height_segs.append(bottom_gap)
            else:
                height_segs.append(level_height - wnd_height)
            total_ht += height_segs[-1]
            height_segs.append(wnd_height)
            total_ht += height_segs[-1]
            if i == levels - 1:
                height_segs.append(top_gap)
                total_ht += height_segs[-1]
        return height_segs, total_ht        
    
    def generate_corner_vertices(self, bm, x, y, height_segs):
        verts = []
        z = 0
        verts.append(bm.verts.new((x,y,z)))
        for seg_ht in height_segs:
            z += seg_ht
            verts.append(bm.verts.new((x,y,z)))
        return verts
    
    def generate_wall(self, bm, wall_segs, start_corners, end_corners):
        w_segs = len(wall_segs)
        norm = (end_corners[0].co - start_corners[0].co).normalized()
        
        prev_start =  start_corners[0]
        prev_end = end_corners[0]
        prev_vectors = []
        faces = []
        extruded_faces = []
        wall_segs_cnt = len(wall_segs)
        i = 0
        for vec_start, vec_end in zip(start_corners[1:], end_corners[1:]):
            l = 0            
            new_vectors = []
            prev_v1 = vec_start
            prev_v2 = prev_start            
            for j, w in enumerate(wall_segs):
                l +=  w
                co = vec_start.co 
                v1 = vec_end
                v2 = prev_end
                if j < wall_segs_cnt - 1:
                    v1 = bm.verts.new((co[0] + l * norm[0], co[1] + l * norm[1], co[2]))
                    new_vectors.append(v1)
                    v2 = prev_vectors[j] if len(prev_vectors) > 0 else bm.verts.new((co[0] + l * norm[0], co[1] + l * norm[1], norm[2]))                
                new_face = bm.faces.new((v1,v2,prev_v2, prev_v1))
                faces.append(new_face)   
                if i % 2 == 1 and j % 2 == 1:
                    extruded_faces.append(new_face)          
                prev_v1 = v1
                prev_v2 = v2
            prev_vectors =  new_vectors
            prev_start = vec_start
            prev_end = vec_end    
            i += 1  
        bm.normal_update()    
        bmesh.ops.inset_individual(bm, faces=extruded_faces, depth=-0.2)
        return faces
            

    def action_common(self, context):      
        # make this configurable
        gap = bpy.context.scene.building_props.gap_prop
        top_gap = bpy.context.scene.building_props.top_gap_prop
        bottom_gap = bpy.context.scene.building_props.bottom_gap_prop
        lengthX = bpy.context.scene.building_props.size_x_prop
        lengthY = bpy.context.scene.building_props.size_y_prop
        levels = bpy.context.scene.building_props.level_count_prop
        level_height = bpy.context.scene.building_props.level_height_prop
        wnd_width = bpy.context.scene.building_props.wnd_width_prop
        wnd_height = bpy.context.scene.building_props.wnd_height_prop
        interval_width = bpy.context.scene.building_props.interval_width_prop
    
        colsX = self.generate_wall_segs(lengthX, wnd_width, interval_width, gap)
        colsY = self.generate_wall_segs(lengthY, wnd_width, interval_width, gap)
        height_segs,total_ht = self.generate_height_segs(levels, level_height, bottom_gap, wnd_height, top_gap)
        
        mesh = bpy.data.meshes.new("mesh")  # add a new mesh
        obj = bpy.data.objects.new("MyObject", mesh)  # add a new object using the mesh

        scene = bpy.context.scene
        scene.objects.link(obj)  # put the object into the scene (link)
        scene.objects.active = obj  # set as the active object in the scene
        obj.select = True  # select object

        mesh = bpy.context.object.data
        bm = bmesh.new()
        
        corners00 = self.generate_corner_vertices(bm,0,0,height_segs)
        corners10 = self.generate_corner_vertices(bm,lengthX,0,height_segs)
        corners01 = self.generate_corner_vertices(bm,0,lengthY,height_segs)
        corners11 = self.generate_corner_vertices(bm,lengthX,lengthY,height_segs)
        self.generate_wall(bm, colsY, corners00, corners01)                
        self.generate_wall(bm, colsX, corners01, corners11)                
        self.generate_wall(bm, colsY, corners11, corners10)                
        self.generate_wall(bm, colsX, corners10, corners00)    
        
#        total_ht = top_gap + level_height * levels + bottom_gap
        verts = [vert for vert in bm.verts if math.isclose(vert.co[2], total_ht, abs_tol = 0.05)]
        if len(verts) > 2:
            bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=True)
        bm.normal_update()  
        
        bm.to_mesh(mesh)  
        bm.free()  # always do this when finished
        mesh.update()        
          
    #end action_common 
   
    def execute(self, context) :
        self.action_common(context)
        return {"FINISHED"}
    #end execute

    def invoke(self, context, event) :
        self.action_common(context)
        return {"FINISHED"}
    #end invoke

#end MakeBuilding

def add_to_menu(self, context) :
    self.layout.operator("mesh.make_building", icon = "PLUGIN")
#end add_to_menu

def register() :
    bpy.utils.register_class(MakeBuilding)
    bpy.utils.register_class(BuildingMakerPanel)
    bpy.utils.register_class(MakerPanelProperties)
    bpy.types.Scene.building_props = bpy.props.PointerProperty(type=MakerPanelProperties)
    bpy.types.INFO_MT_mesh_add.append(add_to_menu)
#end register

def unregister() :
    bpy.utils.unregister_class(MakeBuilding)
    bpy.utils.unregister_class(BuildingMakerPanel)
    bpy.utils.unregister_class(MakerPanelProperties)
    bpy.types.INFO_MT_mesh_add.remove(add_to_menu)
    del bpy.types.Scene.building_props
#end unregister

if __name__ == "__main__" :
    register()
#end if