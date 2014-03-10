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
bl_info = {
    "name": "Panorama Tracker",
    "author": "Dalai Felinto",
    "version": (1, 0),
    "blender": (2, 7, 0),
    "location": "Movie Clip Editor > Tools Panel",
    "description": "Help Stabilize Panorama Footage",
    "warning": "",
    "wiki_url": "https://github.com/dfelinto/Panorama-Tracker",
    "tracker_url": "",
    "category": "Movie Tracking"}

import bpy
from bpy.app.handlers import persistent
from bpy.props import (
    FloatVectorProperty,
    PointerProperty,
    BoolProperty,
    StringProperty,
    EnumProperty,
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

    tracking = movieclip.tracking.objects[movieclip.tracking.active_object_index]
    focus = tracking.tracks.get(settings.focus)
    target = tracking.tracks.get(settings.target)
    frame_current = scene.frame_current

    if not focus or not target: return (0,0,0)

    focus_marker = focus.markers.find_frame(frame_current)
    target_marker = target.markers.find_frame(frame_current)

    if not focus_marker or not target_marker: return (0,0,0)

    vecx = equirectangular_to_sphere(focus_marker.co)
    vecy = equirectangular_to_sphere(target_marker.co)

    if settings.flip:
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

    settings = movieclip.panorama_settings

    tracking = movieclip.tracking.objects[movieclip.tracking.active_object_index]
    focus = tracking.tracks.get(settings.focus)
    target = tracking.tracks.get(settings.target)

    if not focus or not target: return

    frame = scene.frame_current
    marker = focus.markers.find_frame(frame)

    if not marker: return

    return equirectangular_to_sphere(marker.co)


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

        scene = context.scene
        movieclip = context.edit_movieclip
        settings = movieclip.panorama_settings

        return valid_track(movieclip, settings.focus) or valid_track(movieclip, settings.target)

    def execute(self, context):
        scene = context.scene
        movieclip = context.edit_movieclip
        settings = movieclip.panorama_settings

        settings.focus = ""
        settings.target = ""

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

        scene = context.scene
        movieclip = context.edit_movieclip
        settings = movieclip.panorama_settings

        return valid_track(movieclip, settings.focus) and valid_track(movieclip, settings.target)

    def execute(self, context):
        scene = context.scene
        movieclip = context.edit_movieclip
        settings = movieclip.panorama_settings

        scene.panorama_movieclip = movieclip.name

        # 0) if you click twice you flip everything
        settings.flip = not settings.flip

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


# ###############################
#  Select Functions
# ###############################

class CLIP_OT_panorama_select(bpy.types.Operator):
    """"""
    bl_idname = "clip.panorama_select"
    bl_label = "Set Track"
    bl_description = "Prototype function, to be inherited"
    bl_options = {'REGISTER', 'UNDO'}

    _selected_tracks = []

    @classmethod
    def poll(cls, context):
        if not context_clip(context): return False
        if not marker_solo_selected(cls, context): return False

        movieclip = context.edit_movieclip
        settings = movieclip.panorama_settings

        return not cls._valid_track(movieclip, settings)

    def execute(self, context):
        scene = context.scene
        movieclip = context.edit_movieclip
        settings = movieclip.panorama_settings

        track = self._selected_tracks[0].name
        if track in (
            settings.target,
            settings.focus,
            settings.x1,
            settings.x2,
            settings.x3,
            settings.x4):

            self.report({'ERROR'}, "'{0}' already selected as track".format(track))
            return {'CANCELLED'}
        else:
            self._set_track(settings, track)

        return {'FINISHED'}


class CLIP_OT_panorama_focus(CLIP_OT_panorama_select):
    """"""
    bl_idname = "clip.panorama_focus"
    bl_label = "Set Focus Track"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    _selected_tracks = []

    """
    @classmethod
    def poll(cls, context):
        CLIP_OT_panorama_select.poll(cls, context)

    def execute(self, context):
        CLIP_OT_panorama_select.execute(self, context)
    """

    @classmethod
    def _valid_track(cls, movieclip, settings):
        print('focus')
        return valid_track(movieclip, settings.focus)

    def _set_track(self, settings, track):
        settings.focus = track


class CLIP_OT_panorama_target(CLIP_OT_panorama_select):
    """"""
    bl_idname = "clip.panorama_target"
    bl_label = "Set Target Track"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    _selected_tracks = []

    @classmethod
    def _valid_track(cls, movieclip, settings):
        return valid_track(movieclip, settings.target)

    def _set_track(self, settings, track):
        settings.target = track


class CLIP_OT_panorama_x1(CLIP_OT_panorama_select):
    """"""
    bl_idname = "clip.panorama_x1"
    bl_label = "Set X1 Track"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    _selected_tracks = []

    @classmethod
    def _valid_track(cls, movieclip, settings):
        return valid_track(movieclip, settings.x1)

    def _set_track(self, settings, track):
        settings.x1 = track


class CLIP_OT_panorama_x2(CLIP_OT_panorama_select):
    """"""
    bl_idname = "clip.panorama_x2"
    bl_label = "Set X2 Track"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    _selected_tracks = []

    @classmethod
    def _valid_track(cls, movieclip, settings):
        return valid_track(movieclip, settings.x2)

    def _set_track(self, settings, track):
        settings.x2 = track


class CLIP_OT_panorama_x3(CLIP_OT_panorama_select):
    """"""
    bl_idname = "clip.panorama_x3"
    bl_label = "Set X3 Track"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    _selected_tracks = []

    @classmethod
    def _valid_track(cls, movieclip, settings):
        return valid_track(movieclip, settings.x3)

    def _set_track(self, settings, track):
        settings.x3 = track


class CLIP_OT_panorama_x4(CLIP_OT_panorama_select):
    """"""
    bl_idname = "clip.panorama_x4"
    bl_label = "Set X4 Track"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    _selected_tracks = []

    @classmethod
    def _valid_track(cls, movieclip, settings):
        return valid_track(movieclip, settings.x4)

    def _set_track(self, settings, track):
        settings.x4 = track


# ###############################
#  User Interface
# ###############################

class CLIP_PanoramaPanel(bpy.types.Panel):
    ''''''
    bl_label = "Panorama"
    bl_space_type = "CLIP_EDITOR"
    bl_region_type = "TOOLS"

    @classmethod
    def poll(cls, context):
        return context.edit_movieclip

    def draw(self, context):
        layout = self.layout
        movieclip = context.edit_movieclip
        settings = movieclip.panorama_settings

        col = layout.column(align=True)
        col.prop(settings, "method")

        if settings.method == 'TWO_POINTS':
            col.operator("clip.panorama_focus")
            col.operator("clip.panorama_target")

        elif settings.method == 'PARALLEL':
            col.operator("clip.panorama_target", text="Set Focus Target")

            row = col.row(align=True)
            row.operator("clip.panorama_x1")
            row.operator("clip.panorama_x2")

            row = col.row(align=True)
            row.operator("clip.panorama_x3")
            row.operator("clip.panorama_x4")

            col.separator()
            col.prop(settings, "show_preview_axis")

        col.prop(settings, "show_preview_panorama")

        col.operator("clip.panorama_camera", icon="CAMERA_DATA")
        col.operator("clip.panorama_reset", icon="CANCEL")


def update_orientation(self, context):
    """callback called when scene orientation is changed"""
    update_panorama_orientation(context.scene)


@persistent
def update_panorama_orientation(scene):
    """callback function called every frame"""
    world = scene.world
    if not world: return

    nodetree = world.node_tree
    if not nodetree or not nodetree.nodes: return

    tex_env=nodetree.nodes.get("Panorama Environment Texture")
    if not tex_env: return

    tex_env.texture_mapping.rotation = calculate_orientation(scene)


class TrackingPanoramaSettings(bpy.types.PropertyGroup):
    orientation= FloatVectorProperty(name="Orientation", description="Euler rotation", subtype='EULER', default=(0.0,0.0,0.0), update=update_orientation)
    focus = StringProperty()
    target = StringProperty()

    x1 = StringProperty()
    x2 = StringProperty()
    x3 = StringProperty()
    x4 = StringProperty()

    flip = BoolProperty(default=True)

    show_preview_panorama = BoolProperty(
        name="Show Corrected Panorama Preview",
        default=False
        )

    show_preview_axis = BoolProperty(
        name="Show Axis Preview",
        default=False
        )

    method = EnumProperty(
        name="Method",
        description="The type of calibration method to use",
        items=(("TWO_POINTS", "Focus and Target", ""),
               ("PARALLEL", "Focus and Axis", ""),
               ),
        default="TWO_POINTS"
        )


# ###############################
#  Drawing
# ###############################

@bpy.app.handlers.persistent
def draw_callback_px(not_used):
    """"""
    import blf

    scene = bpy.context.scene
    movieclip = bpy.data.movieclips.get(scene.panorama_movieclip)

    if not movieclip: return

    settings = movieclip.panorama_settings
    if (not settings.show_preview_panorama) and (not settings.show_preview_axis): return

    if 1:
        # draw some text
        blf.position(0, 15, 30, 0)
        blf.size(0, 20, 72)
        blf.draw(0, "Hello Panorama World")

    return
"""

    tracking = movieclip.tracking.objects[movieclip.tracking.active_object_index]

    region, width, height = get_clipeditor_region()
    if not region: return

    viewport = Buffer(GL_INT, 4)
    glGetIntegerv(GL_VIEWPORT, viewport)

    # set identity matrices
    view_setup()

    frame_current = scene.frame_current
    coordinates = get_markers_coordinates(tracking, settings, frame_current)
    draw_rectangle(region, width, height, coordinates)

    # restore opengl defaults
    view_reset(viewport)

    glColor4f(1.0, 1.0, 1.0, 1.0)
    font_id = 0  # XXX, need to find out how best to get this.

    # draw some text
    blf.position(font_id, 15, 30, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Hello Word")
"""

# ###############################
#  Register / Unregister
# ###############################
def register():
    bpy.utils.register_module(__name__)

    bpy.types.MovieClip.panorama_settings = PointerProperty(
            type=TrackingPanoramaSettings, name="Tracking Panorama Settings", description="")

    bpy.types.Scene.panorama_movieclip = StringProperty()

    bpy.app.handlers.frame_change_post.append(update_panorama_orientation)

    bpy._panohandle = bpy.types.SpaceClipEditor.draw_handler_add(draw_callback_px, (None,), 'WINDOW', 'POST_PIXEL')


def unregister():
    bpy.utils.unregister_module(__name__)

    del bpy.types.MovieClip.panorama_settings
    del bpy.types.Scene.panorama_movieclip

    bpy.app.handlers.frame_change_post.remove(update_panorama_orientation)
    bpy.types.SpaceClipEditor.draw_handler_remove(bpy._panohandle, 'WINDOW')


if __name__ == '__main__':
    register()
