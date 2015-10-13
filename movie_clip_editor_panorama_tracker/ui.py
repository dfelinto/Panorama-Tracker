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

class CLIP_PanoramaPanel(bpy.types.Panel):
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
        col.operator("clip.panorama_focus")
        col.operator("clip.panorama_target")

        col.separator()
        col.operator("clip.panorama_camera", icon="CAMERA_DATA")
        col.operator("clip.panorama_reset", icon="CANCEL")

        wm = context.window_manager
        preview_enabled = wm.panorama_tracker_preview

        col = layout.column()

        if not preview_enabled:
            col.operator("clip.panorama_preview", text="Preview", icon="PLAY").action='ENABLE'
        else:
            col.operator("clip.panorama_preview", text="Preview", icon="X").action='DISABLE'


# ###############################
#  Register / Unregister
# ###############################
def register():
    bpy.utils.register_class(CLIP_PanoramaPanel)


def unregister():
    bpy.utils.unregister_class(CLIP_PanoramaPanel)
