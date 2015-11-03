#====================== BEGIN GPL LICENSE BLOCK ======================
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
#======================= END GPL LICENSE BLOCK ========================

# <pep8 compliant>

import bpy


# ###############################
# User Interface
# ###############################

class CLIP_PT_panorama(bpy.types.Panel):
    ''''''
    bl_label = "Panorama"
    bl_space_type = "CLIP_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Panorama"

    @classmethod
    def poll(cls, context):
        return context.edit_movieclip

    def draw(self, context):
        layout = self.layout
        movieclip = context.edit_movieclip
        settings = movieclip.panorama_settings

        col = layout.column(align=True)
        col.operator("clip.panorama_camera", icon="CAMERA_DATA")

        col.separator()
        col.prop(settings, "show_preview")


class CLIP_PT_panorama_markers(bpy.types.Panel):
    bl_label = "Markers"
    bl_space_type = "CLIP_EDITOR"
    bl_region_type = "TOOLS"
    bl_category = "Panorama"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        mm = scene.panorama_markers_manager
        row = layout.row()
        row.template_list("UI_UL_list", "template_list_markers", mm,
                          "markers", mm, "active_marker_index", rows=3, maxrows=5)

        sub = row.column()
        subsub = sub.column(align=True)
        subsub.operator("clip.panorama_marker_add", icon='ZOOMIN', text="")
        subsub.operator("clip.panorama_marker_del", icon='ZOOMOUT', text="")

        if len(mm.markers):
            marker = mm.markers[mm.active_marker_index]
            col = layout.column()
            #col.prop(marker, "name")

            frame_smpte = bpy.utils.smpte_from_frame(marker.frame)
            col.label(text="Frame: {0}".format(frame_smpte))

            col.separator()
            box = col.box()
            box.operator("clip.panorama_focus")
            box.operator("clip.panorama_target")
            box.operator("clip.panorama_reset", icon="CANCEL")

            col.separator()
            col.operator("clip.panorama_flip")



# ###############################
#  Register / Unregister
# ###############################

def register():
    bpy.utils.register_class(CLIP_PT_panorama)
    bpy.utils.register_class(CLIP_PT_panorama_markers)


def unregister():
    bpy.utils.unregister_class(CLIP_PT_panorama)
    bpy.utils.unregister_class(CLIP_PT_panorama_markers)
