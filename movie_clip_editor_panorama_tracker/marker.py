import bpy

from bpy.props import (
    StringProperty,
    IntProperty,
    PointerProperty,
    CollectionProperty,
    )


# ###############################
# Update Callback
# ###############################

def update_marker_name(self, context):
    '''rename the marker'''
    scene = context.scene
    marker = self

    frame = marker.frame

    for timeline_marker in scene.timeline_markers:
        if timeline_marker.frame == frame:
            timeline_marker.name = marker.name
            return


# ###############################
# Operators
# ###############################

class CLIP_OT_panorama_marker_add(bpy.types.Operator):
    '''Add a new marker to the scene'''
    bl_idname = "clip.panorama_marker_add"
    bl_label = "Add Markers"

    name = StringProperty(name="Name")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        mm = scene.panorama_markers_manager

        marker = mm.markers.add()
        marker.name = self.name
        marker.frame = scene.frame_current

        # Change the active preset
        mm.active_marker_index = len(mm.markers) - 1

        # Add a new marker marker
        timeline_marker = scene.timeline_markers.new(self.name)
        timeline_marker.frame = scene.frame_current
        return {'FINISHED'}


    def invoke(self, context, event):
        scene = context.scene
        frame = scene.frame_current

        for marker in scene.panorama_markers_manager.markers:
            if marker.frame == frame:
                self.report({'ERROR'}, "Marker \"{0}\" already set for frame {1}".format(marker.name, frame))
                return {'CANCELLED'}

        self.name = bpy.utils.smpte_from_frame(scene.frame_current)
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class CLIP_OT_panorama_marker_del(bpy.types.Operator):
    '''Delete selected marker'''
    bl_idname = "clip.panorama_marker_del"
    bl_label = "Delete Markers"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        mm = scene.panorama_markers_manager

        marker = mm.markers[mm.active_marker_index]
        frame = marker.frame

        # 1) Remove real marker
        for timeline_marker in scene.timeline_markers:
            if timeline_marker.frame == frame:
                scene.timeline_markers.remove(timeline_marker)
                # TODO: remove movieclip markers
                break


        # 2) Remove fake marker
        mm.markers.remove(mm.active_marker_index)
        mm.active_marker_index -= 1
        if mm.active_marker_index < 0:
            mm.active_marker_index = 0

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


# ###############################
# Properties
# ###############################

class PanoramaMarkerInfo(bpy.types.PropertyGroup):
    name = StringProperty(default="", update=update_marker_name)
    frame = IntProperty(name="Frame", min=1, default=1, subtype='TIME')


class PanoramaMarkersManagerInfo(bpy.types.PropertyGroup):
    active_marker_index = IntProperty()
    markers = CollectionProperty(type=PanoramaMarkerInfo)
    template_list_markers = StringProperty(default="marker")


# ###############################
#  Register / Unregister
# ###############################

def register():
    bpy.utils.register_class(PanoramaMarkerInfo)
    bpy.utils.register_class(PanoramaMarkersManagerInfo)
    bpy.types.Scene.panorama_markers_manager = PointerProperty(name="Panorama Markers Manager", type=PanoramaMarkersManagerInfo, options={'HIDDEN'})

    bpy.utils.register_class(CLIP_OT_panorama_marker_add)
    bpy.utils.register_class(CLIP_OT_panorama_marker_del)


def unregister():
    bpy.utils.unregister_class(CLIP_OT_panorama_marker_del)
    bpy.utils.unregister_class(CLIP_OT_panorama_marker_add)

    del bpy.types.Scene.panorama_markers_manager
    bpy.utils.unregister_class(PanoramaMarkersManagerInfo)
    bpy.utils.unregister_class(PanoramaMarkerInfo)

