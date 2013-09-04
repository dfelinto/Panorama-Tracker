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
    "author": "Dalai Felinto and Sebastian Koenig",
    "version": (1, 0),
    "blender": (2, 6, 8),
    "location": "Movie Clip Editor > Tools Panel",
    "description": "Help Stabilize Panorama Footage",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Movie Tracking"}

import bpy
from bpy.app.handlers import persistent
from bpy.props import FloatVectorProperty, PointerProperty, BoolProperty, StringProperty

from mathutils import Vector, Matrix, Euler
from math import (sin, cos, pi, acos, asin, atan2, radians, degrees, sqrt)

# ###############################
# Global Functions
# ###############################

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


def sphere_to_equirectangular(vert):
    """
    convert a 3d point to uv
    """
    theta = asin(vert.z)
    phi = atan2(vert.y, vert.x)

    u = -0.5 * (phi / pi -1)
    v = 0.5 * (2 * theta / pi + 1)

    return u, v


def sphere_to_euler(vecx, vecy, vecz):
    """
    convert sphere orientation vectors to euler
    """
    M = Matrix((vecx, vecy, vecz))
    return M.to_euler()


def sphere_to_3d(vert, euler, radius):
    """
    given a point in the sphere and the euler inclination of the pole
    calculatest he projected point in the plane
    """
    M = euler.to_matrix()
    vert = M * vert
    vert *= radius

    origin = Vector((0,0,radius))
    vert +=  origin
    vector = vert - origin

#    t = (0 - origin[2]) / vector[2]
    t = - radius / (vert[2] - radius)

    floor = origin + t * vector
    return floor


def _3d_to_sphere(vert, euler, radius):
    """
    given a point in the sphere and the euler inclination of the pole
    calculatest he projected point in the plane
    """
    origin = Vector((0,0,radius))
    vert -= origin
    vert /= radius

    M = Euler(euler).to_matrix().inverted()
    vert = M * vert

    return vert


# ###############################
# Main function
# ###############################

def calculate_orientation(scene):
    """return the compound orientation of the tracker + scene orientations"""

    movieclip = bpy.data.movieclips.get(scene.panorama_movieclip)
    if not movieclip: return (0,0,0)

    settings = movieclip.panorama_settings
    #orientation = settings.orientation

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

    # store orientation
    orientation = sphere_to_euler(vecx, nvecy, vecz)

    return (-orientation[0], -orientation[1], -orientation[2])


# ###############################
# Operators
# ###############################

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
        tex_env.image_user.frame_offset = 0
        tex_env.image_user.frame_start = scene.frame_start + movieclip.frame_offset
        tex_env.image_user.frame_duration = scene.frame_end
        tex_env.image_user.use_auto_refresh = True
        tex_env.image_user.use_cyclic = True

        tex_env.texture_mapping.rotation = calculate_orientation(scene)

        # Linking
        background = nodetree.nodes.get("Background")
        nodetree.links.new(tex_env.outputs[0], background.inputs[0])

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
        settings = movieclip.panorama_settings

        return not valid_track(movieclip, settings.focus)

    def execute(self, context):
        scene = context.scene
        movieclip = context.edit_movieclip
        settings = movieclip.panorama_settings

        settings.focus = self._selected_tracks[0].name
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
        settings = movieclip.panorama_settings

        return not valid_track(movieclip, settings.target)

    def execute(self, context):
        scene = context.scene
        movieclip = context.edit_movieclip
        settings = movieclip.panorama_settings

        settings.target = self._selected_tracks[0].name
        return {'FINISHED'}


class CLIP_PanoramaPanel(bpy.types.Panel):
    ''''''
    bl_label = "Panorama"
    bl_space_type = "CLIP_EDITOR"
    bl_region_type = "TOOLS"

    def draw(self, context):
        layout = self.layout
        movieclip = context.edit_movieclip
        settings = movieclip.panorama_settings

        col = layout.column(align=True)
        col.operator("clip.panorama_focus")
        col.operator("clip.panorama_target")

        col.separator()
        col.operator("clip.panorama_camera", icon="CAMERA_DATA")

        col.separator()
        row = col.row()
        row.prop(settings, "orientation", text="")


def update_orientation(self, context):
    """callback called every frame"""
    scene = context.scene
    world = scene.world
    if not world: return

    nodetree = world.node_tree
    tex_env=nodetree.nodes.get("Panorama Environment Texture")
    if not tex_env: return

    tex_env.texture_mapping.rotation = calculate_orientation(scene)


@persistent
def update_panorama_orientation(scene):
    world = scene.world
    if not world: return

    nodetree = world.node_tree
    tex_env=nodetree.nodes.get("Panorama Environment Texture")
    if not tex_env: return

    tex_env.texture_mapping.rotation = calculate_orientation(scene)


def debug_print(scene):
    """routine to print the current selected elements"""
    import pdb
    movieclip = bpy.data.movieclips.get(scene.panorama_movieclip)
    if not movieclip: return

    settings = movieclip.panorama_settings

    tracking = movieclip.tracking.objects[movieclip.tracking.active_object_index]
    focus = tracking.tracks.get(settings.focus)
    target = tracking.tracks.get(settings.target)

    if not focus or not target: return

    frame = scene.frame_current
    print("updating: Movieclip: {} - Focus Marker: {} - Target Marker: {}".format(scene.panorama_movieclip, focus, target))
    print("Focus: {}\nTarget: {}\n".format( \
            equirectangular_to_sphere(focus.markers.find_frame(frame).co), \
            equirectangular_to_sphere(target.markers.find_frame(frame).co) \
            ))
    #pdb.set_trace()


class TrackingPanoramaSettings(bpy.types.PropertyGroup):
    orientation= FloatVectorProperty(name="Orientation", description="Euler rotation", subtype='EULER', default=(0.0,0.0,0.0), update=update_orientation)
    focus = StringProperty()
    target = StringProperty()
    flip = BoolProperty(default=True)


# ###############################
#  Register / Unregister
# ###############################
def register():
    bpy.utils.register_module(__name__)

    bpy.types.MovieClip.panorama_settings = PointerProperty(
            type=TrackingPanoramaSettings, name="Tracking Panorama Settings", description="")

    bpy.types.Scene.panorama_movieclip = StringProperty()

    bpy.app.handlers.frame_change_post.append(update_panorama_orientation)


def unregister():
    bpy.utils.unregister_module(__name__)

    del bpy.types.MovieClip.panorama_settings
    del bpy.types.Scene.panorama_movieclip

    bpy.app.handlers.frame_change_post.remove(update_panorama_orientation)


if __name__ == '__main__':
    register()
