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

from bpy.app.handlers import persistent

# ###############################
# Modal Operator
# ###############################

class CLIP_OT_panorama_preview(bpy.types.Operator):
    """"""
    bl_idname = "clip.panorama_preview"
    bl_label = "Preview Panorama Toggle"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None
    _handle = None
    _area_hash = -1

    action = bpy.props.EnumProperty(
        description="",
        items=(("ENABLE", "Enable", "Enable"),
               ("DISABLE", "Disable", "Disable"),
               ("TOGGLE", "Toggle", "Toggle"),
               ),
        default="TOGGLE",
        options={'SKIP_SAVE'},
        )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        wm = context.window_manager

        if self.action == 'ENABLE':
            wm.panorama_tracker_preview = True
        else:
            wm.panorama_tracker_preview = False

        return {'CANCELLED'}


# ############################################################
# Callbacks
# ############################################################

@persistent
def panorama_tracker_load_pre(dummy):
    wm = bpy.context.window_manager
    wm.panorama_tracker_preview = False


@persistent
def panorama_tracker_load_post(dummy):
    wm = bpy.context.window_manager
    wm.panorama_tracker_preview = False


# ###############################
#  Register / Unregister
# ###############################
def register():
    bpy.app.handlers.load_pre.append(panorama_tracker_load_pre)
    bpy.app.handlers.load_pre.append(panorama_tracker_load_post)

    bpy.utils.register_class(CLIP_OT_panorama_preview)
    bpy.types.WindowManager.panorama_tracker_preview = bpy.props.BoolProperty(
            default=False,
            options={'HIDDEN'},
            )


def unregister():
    bpy.app.handlers.load_pre.remove(panorama_tracker_load_pre)
    bpy.app.handlers.load_pre.remove(panorama_tracker_load_post)

    bpy.utils.unregister_class(CLIP_OT_panorama_preview)
    del bpy.types.WindowManager.panorama_tracker_preview
