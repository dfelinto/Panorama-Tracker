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

from bpy.props import (
        BoolProperty,
        CollectionProperty,
        FloatVectorProperty,
        PointerProperty,
        StringProperty,
        )

from mathutils import (
        Vector,
        Matrix,
        Euler,
        )

from math import (
        sin,
        cos,
        pi,
        acos,
        asin,
        atan2,
        radians,
        degrees,
        sqrt,
        )

from .preview import show_preview_update

# ###############################
# Global Functions
# ###############################

def get_sequence_start(image):
    """returns the initial frame of the selected sequence"""
    import os

    if image.source == 'MOVIE':
        return 1
    else:
        filepath = image.filepath
        file = os.path.basename(filepath)
        name = file[:file.rfind('.')]

        start = 0
        end = -1

        for i in range(len(name)):
            d = name[-(i+1)]
            if str.isdigit(d):
                end = len(name) - i
                break

        if end == -1:
            return 1

        name = name[:end]

        for i in range(len(name)):
            d = name[-(i+1)]
            if not str.isdigit(d):
                start = len(name) - i
                break

        name = name[start:]
        return int(name)


def get_image(imagepath, fake_user=True):
    """get blender image for a given path, or load one"""
    image = None

    for img in bpy.data.images:
      if img.filepath == imagepath:
        image=img
        break

    if not image:
      image=bpy.data.images.load(imagepath)
      image.use_fake_user = fake_user

    return image


def context_clip(context):
    sc = context.space_data

    if sc.type != 'CLIP_EDITOR':
        return False

    if not sc.clip or not context.edit_movieclip:
        return False

    if sc.view != 'CLIP':
        return False

    return True


def marker_solo_selected(cls, context):
    movieclip = context.edit_movieclip
    tracking = movieclip.tracking.objects[movieclip.tracking.active_object_index]

    cls._selected_tracks = []
    for track in tracking.tracks:
        if track.select:
            cls._selected_tracks.append(track)

    return len(cls._selected_tracks) == 1


def valid_track(movieclip, name):
    """returns if there a track with the name"""
    if not movieclip or name == "": return False

    tracking = movieclip.tracking.objects[movieclip.tracking.active_object_index]
    track = tracking.tracks.get(name)

    return track

# ###############################
#  Geometry Functions
# ###############################

def equirectangular_to_sphere(uv):
    """
    convert a 2d point to 3d
    uv : 0,0 (bottom left) 1,1 (top right)
    uv : +pi, -pi/2 (bottom left) -pi, +pi/2 (top right)
    """
    u,v = uv

    phi = (0.5 - u) * 2 * pi
    theta = (v - 0.5) * pi
    r = cos(theta)

    x = cos(phi) * r
    y = sin(phi) * r
    z = sin(theta)

    return Vector((x,y,z))


def sphere_to_euler(vecx, vecy, vecz):
    """
    convert sphere orientation vectors to euler
    """
    M = Matrix((vecx, vecy, vecz))
    return M.to_euler()


# ###############################
# Main function
# ###############################

def calculate_orientation(scene):
    """return the compound orientation of the tracker + scene orientations"""

    movieclip = bpy.data.movieclips.get(scene.panorama_movieclip)
    if not movieclip: return (0,0,0)

    settings = movieclip.panorama_settings
    marker = get_marker(scene, movieclip, create=False, current_time=True)

    if not marker: return (0,0,0)

    tracking = movieclip.tracking.objects[movieclip.tracking.active_object_index]
    focus = tracking.tracks.get(marker.focus)
    target = tracking.tracks.get(marker.target)
    frame_current = scene.frame_current

    if not focus or not target: return (0,0,0)

    focus_marker = focus.markers.find_frame(frame_current)
    target_marker = target.markers.find_frame(frame_current)

    if not focus_marker or not target_marker: return (0,0,0)

    vecx = equirectangular_to_sphere(focus_marker.co)
    vecy = equirectangular_to_sphere(target_marker.co)

    if marker.use_flip:
        vecz = vecx.cross(vecy)
    else:
        vecz = vecy.cross(vecx)
    vecz.normalize()

    # retarget y axis again
    nvecy = vecz.cross(vecx)
    nvecy.normalize()

    # store orientation
    orientation = sphere_to_euler(vecx, nvecy, vecz)
    orientation = (settings.orientation.to_matrix() * orientation.to_matrix()).to_euler()

    return (-orientation[0], -orientation[1], -orientation[2])


def set_3d_cursor(scene):
    movieclip = bpy.data.movieclips.get(scene.panorama_movieclip)
    if not movieclip: return

    marker = get_marker(scene, movieclip, create=False)

    tracking = movieclip.tracking.objects[movieclip.tracking.active_object_index]
    focus = tracking.tracks.get(marker.focus)
    target = tracking.tracks.get(marker.target)

    if not focus or not target: return

    frame = scene.frame_current
    return equirectangular_to_sphere(focus.markers.find_frame(frame).co)


# ###############################
# Operators
# ###############################

class CLIP_OT_panorama_reset(bpy.types.Operator):
    """"""
    bl_idname = "clip.panorama_reset"
    bl_label = "Reset Tracks"
    bl_description = "Reset the selected tracks"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context_clip(context):
            return False

        movieclip = context.edit_movieclip
        marker = get_marker(context.scene, movieclip, create=False)

        return marker and (valid_track(movieclip, marker.focus) or valid_track(movieclip, marker.target))

    def execute(self, context):
        scene = context.scene
        movieclip = context.edit_movieclip
        marker = get_marker(context.scene, movieclip, create=False)

        if marker:
            marker.focus = ""
            marker.target = ""

        return {'FINISHED'}


class CLIP_OT_panorama_camera(bpy.types.Operator):
    """"""
    bl_idname = "clip.panorama_camera"
    bl_label = "Panorama Camera"
    bl_description = "Create/adjust a panorama camera"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context_clip(context):
            return False

        movieclip = context.edit_movieclip
        marker = get_marker(context.scene, movieclip, create=False)

        return marker and valid_track(movieclip, marker.focus) and valid_track(movieclip, marker.target)

    def execute(self, context):
        scene = context.scene
        movieclip = context.edit_movieclip
        settings = movieclip.panorama_settings

        scene.panorama_movieclip = movieclip.name

        # 1) creates a new camera if no camera is selected
        camera = bpy.data.objects.get('Panorama Camera')
        if not camera:
            camera = bpy.data.objects.new('Panorama Camera', bpy.data.cameras.new('Panorama Camera'))
            scene.objects.link(camera)
            camera.data.passepartout_alpha = 1.0

        # force render engine to be Cycles
        scene.render.engine = 'CYCLES'
        if scene.render.engine != 'CYCLES':
            self.report({'ERROR'}, "Cycles engine required.\n")
            return {'CANCELLED'}

        camera.data.type = 'PANO'
        camera.data.cycles.panorama_type = 'EQUIRECTANGULAR'

        camera.location[2] = 0.0
        camera.rotation_euler = Euler((pi*0.5, 0, -pi*0.5))
        scene.camera = camera

        imagepath = movieclip.filepath
        image = get_image(imagepath)

        if image.source != 'MOVIE':
            image.source = 'SEQUENCE'

        if not scene.world:
            scene.world= bpy.data.worlds.new(name='Panorama')

        world = scene.world
        world.use_nodes=True
        world.cycles.sample_as_light = True
        nodetree = world.node_tree

        tex_env=nodetree.nodes.get("Panorama Environment Texture")
        if not tex_env:
            tex_env=nodetree.nodes.new('ShaderNodeTexEnvironment')
            tex_env.name = "Panorama Environment Texture"
            tex_env.location = (-200, 280)

        tex_env.image = image
        tex_env.image_user.frame_start = movieclip.frame_start
        tex_env.image_user.frame_offset = movieclip.frame_offset + get_sequence_start(image) - 1
        tex_env.image_user.frame_duration = scene.frame_end + 1
        tex_env.image_user.use_auto_refresh = True
        tex_env.image_user.use_cyclic = True

        # start with the mapping matching the render and current frame
        if 'vector_type' in dir (tex_env.texture_mapping):
            tex_env.texture_mapping.vector_type = 'POINT'
        tex_env.texture_mapping.rotation = (0,0,0)

        # Linking
        background = nodetree.nodes.get("Background")
        nodetree.links.new(tex_env.outputs[0], background.inputs[0])

        # Render Settings
        scene.render.resolution_x = movieclip.size[0]
        scene.render.resolution_y = movieclip.size[1]
        scene.render.resolution_percentage = 100
        scene.cycles.samples = 1
        scene.cycles.max_bounces = 0

        # Set the cursor
        scene.cursor_location = set_3d_cursor(scene)

        # Uses the current orientation as the final one
        settings.orientation = (0,0,0)
        orientation = calculate_orientation(scene)
        settings.orientation = Euler((-orientation[0], -orientation[1], -orientation[2])).to_matrix().inverted().to_euler()

        return {'FINISHED'}


class CLIP_OT_panorama_focus(bpy.types.Operator):
    """"""
    bl_idname = "clip.panorama_focus"
    bl_label = "Set Focus Track"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    _selected_tracks = []

    @classmethod
    def poll(cls, context):
        if not context_clip(context): return False
        if not marker_solo_selected(cls, context): return False

        movieclip = context.edit_movieclip
        marker = get_marker(context.scene, movieclip, create=False)

        return (not marker) or (not valid_track(movieclip, marker.focus))

    def execute(self, context):
        movieclip = context.edit_movieclip
        marker = get_marker(context.scene, movieclip)

        track = self._selected_tracks[0].name

        if marker.target == track:
            self.report({'ERROR'}, "'{0}' already selected as Target Track".format(track))
            return {'CANCELLED'}
        else:
            marker.focus = track

        return {'FINISHED'}


class CLIP_OT_panorama_target(bpy.types.Operator):
    """"""
    bl_idname = "clip.panorama_target"
    bl_label = "Set Target Track"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    _selected_tracks = []

    @classmethod
    def poll(cls, context):
        if not context_clip(context): return False
        if not marker_solo_selected(cls, context): return False

        movieclip = context.edit_movieclip
        marker = get_marker(context.scene, movieclip, create=False)

        return (not marker) or (not valid_track(movieclip, marker.target))

    def execute(self, context):
        movieclip = context.edit_movieclip
        marker = get_marker(context.scene, movieclip)

        track = self._selected_tracks[0].name

        if marker.focus == track:
            self.report({'ERROR'}, "'{0}' already selected as Focus Track".format(track))
            return {'CANCELLED'}
        else:
            marker.target = track

        return {'FINISHED'}


class CLIP_OT_panorama_flip(bpy.types.Operator):
    """"""
    bl_idname = "clip.panorama_flip"
    bl_label = "Flip Zenith/Nadir"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context_clip(context):
            return False

        movieclip = context.edit_movieclip
        marker = get_marker(context.scene, movieclip, create=False)

        return marker and valid_track(movieclip, marker.focus) and valid_track(movieclip, marker.target)

    def execute(self, context):
        scene = context.scene
        movieclip = context.edit_movieclip
        marker = get_marker(scene, movieclip)

        marker.use_flip = not marker.use_flip

        update_panorama_orientation(scene)
        context.area.tag_redraw()
        return {'FINISHED'}


def get_marker(scene, movieclip, create=True, current_time=False):
    """create a marker if non existent"""
    mm = scene.panorama_markers_manager

    if not len(mm.markers):
        return None

    if current_time:
        frame_current = scene.frame_current
        frame_previous = 0
        scene_marker = mm.markers[mm.active_marker_index]

        for marker in mm.markers:
            frame = marker.frame

            if frame <= frame_current and \
               frame > frame_previous:
                frame_previous = frame
                scene_marker = marker

    else:
        scene_marker = mm.markers[mm.active_marker_index]

    frame = str(scene_marker.frame)

    settings = movieclip.panorama_settings
    marker = settings.markers.get(frame)

    if create and not marker:
        marker = settings.markers.add()
        marker.name = frame

    return marker


def update_orientation(self, context):
    """callback called when scene orientation is changed"""
    update_panorama_orientation(context.scene)


@persistent
def update_panorama_orientation(scene):
    """callback function called every frame"""
    pg = bpy.panorama_globals
    is_enabled = pg.is_enabled
    orientation = None

    if is_enabled:
        orientation = calculate_orientation(scene)
        pg.orientation = mapping_node_order_flip(orientation).to_matrix().inverted().to_4x4()

    world = scene.world
    if not world: return

    nodetree = world.node_tree
    if not nodetree or not nodetree.nodes: return

    tex_env=nodetree.nodes.get("Panorama Environment Texture")
    if not tex_env: return

    if orientation == None:
        orientation = calculate_orientation(scene)

    if bpy.app.version <= (2, 73, 4):
        tex_env.texture_mapping.rotation = orientation
    else:
        tex_env.texture_mapping.rotation = mapping_node_order_flip(orientation)


def mapping_node_order_flip(orientation):
    """
    Flip euler order of mapping shader node
    see: Blender #a1ffb49
    """
    rot = Euler(orientation)
    rot.order = 'ZYX'
    quat = rot.to_quaternion()
    return quat.to_euler('XYZ')


# ###############################
#  Properties
# ###############################

class TrackingPanoramaMarkerInfo(bpy.types.PropertyGroup):
    name = StringProperty()
    use_flip = BoolProperty()
    focus = StringProperty()
    target = StringProperty()


class TrackingPanoramaSettings(bpy.types.PropertyGroup):
    orientation= FloatVectorProperty(name="Orientation", description="Euler rotation", subtype='EULER', default=(0.0,0.0,0.0), update=update_orientation)
    show_preview = BoolProperty(default=False, name="Show Preview", update=show_preview_update)
    markers = CollectionProperty(type=TrackingPanoramaMarkerInfo)


# ###############################
#  Register / Unregister
# ###############################

def register():
    bpy.utils.register_class(TrackingPanoramaMarkerInfo)
    bpy.utils.register_class(TrackingPanoramaSettings)
    bpy.utils.register_class(CLIP_OT_panorama_reset)
    bpy.utils.register_class(CLIP_OT_panorama_target)
    bpy.utils.register_class(CLIP_OT_panorama_camera)
    bpy.utils.register_class(CLIP_OT_panorama_focus)
    bpy.utils.register_class(CLIP_OT_panorama_flip)

    bpy.types.MovieClip.panorama_settings = PointerProperty(
            type=TrackingPanoramaSettings, name="Tracking Panorama Settings", description="")

    bpy.types.Scene.panorama_movieclip = StringProperty()

    bpy.app.handlers.frame_change_post.append(update_panorama_orientation)


def unregister():

    del bpy.types.MovieClip.panorama_settings
    del bpy.types.Scene.panorama_movieclip

    bpy.app.handlers.frame_change_post.remove(update_panorama_orientation)

    bpy.utils.unregister_class(CLIP_OT_panorama_flip)
    bpy.utils.unregister_class(CLIP_OT_panorama_focus)
    bpy.utils.unregister_class(CLIP_OT_panorama_camera)
    bpy.utils.unregister_class(CLIP_OT_panorama_target)
    bpy.utils.unregister_class(CLIP_OT_panorama_unreset)
    bpy.utils.unregister_class(TrackingPanoramaSettings)
    bpy.utils.unregister_class(TrackingPanoramaMarkerInfo)
