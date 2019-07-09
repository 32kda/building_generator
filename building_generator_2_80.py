# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# ----------------------------------------------------------
# Author: Dmitry Karpenko (32kda), OnPositive
# ----------------------------------------------------------

# ----------------------------------------------
# Define Addon info
# ----------------------------------------------

bl_info = {
    "name": "Building Generator",
    "author": "Dmitry Karpenko(32kda)",
    "location": "View3D > Add > Mesh > Building",
    "version": (0, 2, 0),
    "blender": (2, 8, 0),
    "description": "Generate low-poly buildings by params - with, height, level count, window size etc.",
    "category": "Add Mesh"
}

import math
import bpy
import mathutils
import bmesh
from collections import OrderedDict
from mathutils import Vector
from bpy.types import Operator, PropertyGroup, Object, Panel
from bpy.props import StringProperty, FloatProperty, BoolProperty, IntProperty
from bpy.utils import register_class, unregister_class

def on_property_update(_, context):
    props = context.object.building_props
    print('Hello, world!' + props.size_x_prop)


class MAKER_PT_Building(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    #bl_context = "objectmode"
    bl_category = "Create"
    bl_label = "Add Building"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True  # Active single-column layout

        obj = context.object

        if obj is None or obj.type != "MESH":
            # add operators

            return

        props = obj.building_props

        col = self.layout.column(align=True)

        row = layout.row()

        row.separator()

        col.prop(props, 'size_x_prop')
        col.prop(props, 'size_y_prop')
        col.prop(props, 'level_count_prop')
        col.prop(props, 'level_height_prop')
        col.prop(props, 'wnd_width_prop')
        col.prop(props, 'wnd_height_prop')
        col.prop(props,'interval_width_prop')
        col.prop(props, 'gap_prop')
        col.prop(props, 'top_gap_prop')
        col.prop(props, 'bottom_gap_prop')

        col.operator("mesh.make_building", text="Add Building")
    # end draw

# end MAKER_PT_Building

# ------------------------------------------------------------------
# Define property group class to create or modify
# ------------------------------------------------------------------


class MAKER_PT_Properties(PropertyGroup):
    size_x_prop : IntProperty(
        name='X Size', min=1, default=30,
        description='X Size of building, meters',
        subtype="DISTANCE", update=on_property_update
    )
    size_y_prop : IntProperty(
        name='Y Size', min=1, default=10,
        description='Y Size of building, meters',
        subtype="DISTANCE", update=on_property_update
    )
    level_count_prop : IntProperty(
        name='Level count', min=1, default=3,
        description='Building levels count',
        update=on_property_update
    )
    level_height_prop : FloatProperty(
        name='Level height', min=1, default=3,
        description='Building level height, meters',
        subtype="DISTANCE", update=on_property_update
    )
    wnd_width_prop : FloatProperty(
        name='Window width', min=0.1, default=1.46,
        description='Window width, meters',
    )
    wnd_height_prop : FloatProperty(
        name='Window height', min=0.1, default=1.46,
        description='Window height, meters',
    )
    interval_width_prop : FloatProperty(
        name='Interval width', min=0.1, default=1.5,
        description='Horizontal interval width, meters',
    )
    gap_prop : FloatProperty(
        name='Min horiz gap', min=0.1, default=3,
        description='Min left/right gap size , meters',
    )
    top_gap_prop : FloatProperty(
        name='Top gap', min=0.1, default=1,
        description='Top gap size , meters',
    )
    bottom_gap_prop : FloatProperty(
        name='Bottom gap', min=0.1, default=2.5,
        description='Bottom gap size , meters',
    )


class MakeBuilding(bpy.types.Operator):
    bl_idname = "mesh.make_building"
    bl_label = "Building"
    bl_options = {"REGISTER", "UNDO"}

    def draw(self, context):
        #XXX props are added here instead of seperate panel. implement correct handling
        layout = self.layout
        layout.use_property_split = True  # Active single-column layout

        obj = context.object

        if obj is None or obj.type != "MESH":
            # add operators

            return

        props = obj.building_props

        col = self.layout.column(align=True)

        row = layout.row()

        row.separator()

        col.prop(props, 'size_x_prop')
        col.prop(props, 'size_y_prop')
        col.prop(props, 'level_count_prop')
        col.prop(props, 'level_height_prop')
        col.prop(props, 'wnd_width_prop')
        col.prop(props, 'wnd_height_prop')
        col.prop(props, 'interval_width_prop')
        col.prop(props, 'gap_prop')
        col.prop(props, 'top_gap_prop')
        col.prop(props, 'bottom_gap_prop')

    # end draw

    @staticmethod
    def generate_stripe(vectors, faces, cols, i, size, x, y, z):
        for j, w in enumerate(cols):
            vectors.append(Vector((x, y, z)))
            x += w
            if i > 0 and j > 0:
                faces.append([(i - 1) * size + j - 1, (i - 1) *
                              size + j, i * size + j, i * size + j - 1])

        vectors.append(Vector((x, y, z)))
        if i > 0:
            faces.append([(i - 1) * size + size - 2,
                          (i - 1) * size + size - 1,
                          i * size + size - 1,
                          i * size + size - 2])
    # end generate_stripe

    @staticmethod
    def generate_wall_segs(length, wnd_width, interval_width, min_gap):
        """
        Generates wall segments (windows, intervals) lengths array
        :param length: wall length, m
        :param wnd_width: window width, m
        :param interval_width: interval width, m
        :param min_gap: minimal left/right gap, m
        :return: segment lengths array
        """
        cnt = int((length - (wnd_width + min_gap * 2)) /
                  (wnd_width + interval_width))

        real_gap = (1.0 * length - (wnd_width + interval_width)
                    * cnt - wnd_width) / 2

        cols = [real_gap]
        for i in range(cnt):
            cols.append(wnd_width)
            cols.append(interval_width)
        cols.append(wnd_width)
        cols.append(real_gap)
        return cols

    @staticmethod
    def generate_height_segs(
            levels,
            level_height,
            bottom_gap,
            wnd_height,
            top_gap):
        """
        Generate height segments array
        :param levels: Building levels count
        :param level_height: level height, m
        :param bottom_gap: bottom gap, m
        :param wnd_height: wnd height,m
        :param top_gap: top gap, m
        :return: heights list
        """
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

    @staticmethod
    def generate_corner_vertices(bm, x, y, height_segs):
        """
        Generates vertices on building corner
        :param bm: BMesh object to create vertices with
        :param x: corner x coordinate
        :param y: corner y coordinate
        :param height_segs: height segments array generated by generate_height_segs method
        :return: generated vertices list
        """
        z = 0
        verts = [bm.verts.new((x, y, z))]
        for seg_ht in height_segs:
            z += seg_ht
            verts.append(bm.verts.new((x, y, z)))
        return verts

    @staticmethod
    def generate_wall(bm, wall_segs, start_corners, end_corners):
        """
        Generate wall geometry with extruding widows
        :param bm: BMesh object to create geometry with
        :param wall_segs:  wall segments lengths array (see generate_wall_segs)
        :param start_corners: wall start corner vertices list, see generate_corner_vertices
        :param end_corners: wall end corner vertices list, see generate_corner_vertices
        :return: created top vertices list for generating roof based on them
        """
        w_segs = len(wall_segs)
        norm = (end_corners[0].co - start_corners[0].co).normalized()

        prev_start = start_corners[0]
        prev_end = end_corners[0]
        prev_vectors = []
        extruded_faces = []
        wall_segs_cnt = len(wall_segs)
        i = 0
        for vec_start, vec_end in zip(start_corners[1:], end_corners[1:]):
            l = 0
            new_vectors = []
            prev_v1 = vec_start
            prev_v2 = prev_start
            for j, w in enumerate(wall_segs):
                l += w
                co = vec_start.co
                v1 = vec_end
                v2 = prev_end
                if j < wall_segs_cnt - 1:
                    v1 = bm.verts.new(
                        (co[0] + l * norm[0], co[1] + l * norm[1], co[2]))
                    new_vectors.append(v1)
                    v2 = prev_vectors[j] if len(prev_vectors) > 0 else bm.verts.new(
                        (co[0] + l * norm[0], co[1] + l * norm[1], norm[2]))
                new_face = bm.faces.new((v1, v2, prev_v2, prev_v1))
                if i % 2 == 1 and j % 2 == 1:
                    extruded_faces.append(new_face)
                prev_v1 = v1
                prev_v2 = v2
            prev_vectors = new_vectors
            prev_start = vec_start
            prev_end = vec_end
            i += 1
        bm.normal_update()
        bmesh.ops.inset_individual(bm, faces=extruded_faces, depth=-0.2)
        return prev_vectors

    def action_common(self, context):
        gap = bpy.context.object.building_props.gap_prop
        top_gap = bpy.context.object.building_props.top_gap_prop
        bottom_gap = bpy.context.object.building_props.bottom_gap_prop
        length_x = bpy.context.object.building_props.size_x_prop
        length_y = bpy.context.object.building_props.size_y_prop
        levels = bpy.context.object.building_props.level_count_prop
        level_height = bpy.context.object.building_props.level_height_prop
        wnd_width = bpy.context.object.building_props.wnd_width_prop
        wnd_height = bpy.context.object.building_props.wnd_height_prop
        interval_width = bpy.context.object.building_props.interval_width_prop

        location = bpy.context.scene.cursor.location

        self.generate_building(
            location.x,
            location.y,
            length_x,
            length_y,
            level_height,
            levels,
            bottom_gap,
            gap,
            top_gap,
            interval_width,
            wnd_height,
            wnd_width)

    def generate_building(
            self,
            cursor_x,
            cursor_y,
            length_x,
            length_y,
            level_height,
            levels,
            bottom_gap,
            gap,
            top_gap,
            interval_width,
            wnd_height,
            wnd_width):
        """
        Key method responsible for building mesh generation
        :param cursor_x: cursor x position
        :param cursor_y: cursor y position
        :param length_x: Building X size, m
        :param length_y: Building Y size, m
        :param level_height: Building level height, m
        :param levels: Building level count
        :param bottom_gap: Bottom gap, m
        :param gap: left/right min gap, m
        :param top_gap: top gap, m
        :param interval_width: interval width, m
        :param wnd_height: window height, m
        :param wnd_width: window width, m
        """
        cols_x = MakeBuilding.generate_wall_segs(
            length_x, wnd_width, interval_width, gap)
        cols_y = MakeBuilding.generate_wall_segs(
            length_y, wnd_width, interval_width, gap)
        height_segs, total_ht = MakeBuilding.generate_height_segs(
            levels, level_height, bottom_gap, wnd_height, top_gap)
        mesh = bpy.data.meshes.new("mesh")  # add a new mesh
        # add a new object using the mesh
        obj = bpy.data.objects.new("Building", mesh)
        scene = bpy.context.scene
        scene.collection.objects.link(obj)  # put the object into the scene (link)
        bpy.context.view_layer.objects.active = obj  # set as the active object in the scene
        obj.select_set(True)  # select object
        mesh = bpy.context.object.data
        bm = bmesh.new()
        delta_x = cursor_x - length_x / 2
        delta_y = cursor_y - length_y / 2
        corners00 = MakeBuilding.generate_corner_vertices(
            bm, delta_x, delta_y, height_segs)
        corners10 = MakeBuilding.generate_corner_vertices(
            bm, delta_x + length_x, delta_y, height_segs)
        corners01 = MakeBuilding.generate_corner_vertices(
            bm, delta_x, delta_y + length_y, height_segs)
        corners11 = MakeBuilding.generate_corner_vertices(
            bm, delta_x + length_x, delta_y + length_y, height_segs)
        vecs1 = MakeBuilding.generate_wall(bm, cols_y, corners00, corners01)
        vecs2 = MakeBuilding.generate_wall(bm, cols_x, corners01, corners11)
        vecs3 = MakeBuilding.generate_wall(bm, cols_y, corners11, corners10)
        vecs4 = MakeBuilding.generate_wall(bm, cols_x, corners10, corners00)
        vecs = list(OrderedDict.fromkeys([corners00[-1]] + vecs1 + [corners01[-1]] + vecs2 + [corners11[-1]]  + vecs3 + [corners10[-1]] + vecs4))

        if len(vecs) > 2:
            bm.faces.new(vecs)

        bm.normal_update()
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

    # end action_common

    def execute(self, context):
        self.action_common(context)
        return {"FINISHED"}
    # end execute

    def invoke(self, context, event):
        self.action_common(context)
        return {"FINISHED"}
    # end invoke

# end MakeBuilding


def add_to_menu(self, context):
    self.layout.operator("mesh.make_building", icon="PLUGIN")
# end add_to_menu

classes = (
    MakeBuilding,
    MAKER_PT_Building,
    MAKER_PT_Properties,
)

def register():
    for clazz in classes:
        register_class(clazz)
    Object.building_props = bpy.props.PointerProperty(
        type=MAKER_PT_Properties,
        name="building_props",
        description="Generated building properties"
    )
    bpy.types.VIEW3D_MT_mesh_add.append(add_to_menu)
# end register


def unregister():
    for clazz in reversed(classes):
        unregister_class(clazz)
    bpy.types.VIEW3D_MT_mesh_add.remove(add_to_menu)
    del Object.building_props
# end unregister


if __name__ == "__main__":
    register()
# end if
