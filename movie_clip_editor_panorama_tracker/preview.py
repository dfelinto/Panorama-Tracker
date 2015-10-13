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

from .opengl_helper import (
        calculate_image_size,
        create_image,
        create_shader,
        delete_image,
        update_image,
        view_reset,
        view_setup,
        )

from bgl import *

from mathutils import (
        Matrix,
        )

from math import (
        radians,
        )

TODO = False


# ###############################
# Callback
# ###############################

def show_preview_update(settings, context):
    movieclip = context.edit_movieclip
    pg = bpy.panorama_globals

    if settings.show_preview:
        panorama_setup(pg, movieclip)

    else:
        panorama_reset(pg)


# ###############################
# Utils
# ###############################

def resize(panorama_globals, movieclip, viewport):
    """we can run every frame or only when width/height change"""
    pg = bpy.panorama_globals

    width = viewport[2]
    height = viewport[3]

    # power of two dimensions
    buffer_width, buffer_height = calculate_image_size(width, height)

    if (buffer_width == pg.buffer_width) and \
       (buffer_height == pg.buffer_height):
        return

    # remove old textures
    panorama_reset(pg)
    pg.is_enabled = True

    pg.buffer_width = width
    pg.buffer_height = height

    # image to dump screen buffer
    pg.color_texture = create_image(pg.buffer_width, pg.buffer_height, GL_RGBA)


def get_glsl_shader(shader_file):
    import os
    folderpath = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(folderpath, shader_file)
    f = open(filepath, 'r')
    data = f.read()
    f.close()
    return data


def view_setup():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glOrtho(0, 1, 0, 1, -15, 15)
    gluLookAt(0.0, 0.0, 1.0, 0.0,0.0,0.0, 0.0,1.0,0.0)

def get_markers_coordinates(tracking, settings, frame=1):
    coordinates =[]
    for name in (settings.target, settings.focus):
        track = tracking.tracks.get(name)
        if not track:
            coordinates.append((0,0))
            continue

        marker = track.markers.find_frame(frame)
        if not marker:
            coordinates.append((0,0))
            continue

        coordinates.append(marker.co)

    return coordinates


def draw_rectangle(region, width, height):
    coordinates=((1,1),(0,1),(0,0),(1,0))
    texco = [(1, 1), (0, 1), (0, 0), (1,0)]

    verco = []
    for x,y in coordinates:
        co = list(region.view2d.view_to_region(x,y, False))
        co[0] /= float(width)
        co[1] /= float(height)
        verco.append(co)

    glPolygonMode(GL_FRONT_AND_BACK , GL_FILL)
    glBegin(GL_QUADS)

    for i in range(4):
        glColor4f(1.0, 1.0, 1.0, 0.0)
        glTexCoord3f(texco[i][0], texco[i][1], 0.0)
        glVertex2f(verco[i][0], verco[i][1])
    glEnd()


def get_clipeditor_region():
    for area in bpy.context.screen.areas:
        if area.type == 'CLIP_EDITOR':
            for region in area.regions:
                if region.type == 'WINDOW':

                    bot = region.view2d.view_to_region(0.0, 0.0)
                    top = region.view2d.view_to_region(1.0, 1.0)

                    if bot[0] == 12000 or top[0] == 12000:
                        return None, [0,0,0,0]

                    width = top[0] - bot[0]
                    height = top[1] - bot[1]

                    return region, [bot[0], bot[1], width, height]

    return None, [0,0,0,0]


# ###############################
# Setup and Reset
# ###############################

def panorama_setup(panorama_globals, movieclip):
    pg = panorama_globals

    if pg.is_enabled:
        return False

    pg.is_enabled = True

    region, viewport = get_clipeditor_region()

    # create initial image
    resize(pg, movieclip, viewport)

    # glsl shaders
    fragment_shader = get_glsl_shader('preview.fp')
    pg.program = create_shader(fragment_shader, type=GL_FRAGMENT_SHADER)

    from . import core
    core.update_panorama_orientation(bpy.context.scene)


def panorama_reset(panorama_globals):
    pg = panorama_globals

    if not pg.is_enabled:
        return False

    pg.is_enabled = False

    if pg.color_texture:
        delete_image(pg.color_texture)

    TODO # delete shader


# ###############################
# Main Drawing Routine
# ###############################

def setup_uniforms(program, color_texture, transformation_matrix):
    uniform = glGetUniformLocation(program, "color_buffer")
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, color_texture)
    if uniform != -1: glUniform1i(uniform, 0)

    uniform = glGetUniformLocation(program, "transformation_matrix")
    if uniform != -1: glUniformMatrix4fv(uniform, 1, 0, transformation_matrix)


@persistent
def draw_panorama_callback_px(not_used):
    """"""
    pg = bpy.panorama_globals

    if not pg.is_enabled: return

    movieclip = bpy.context.edit_movieclip
    scene = bpy.context.scene

    if not movieclip: return

    settings = movieclip.panorama_settings
    if not settings.show_preview: return

    tracking = movieclip.tracking.objects[movieclip.tracking.active_object_index]

    region, viewport = get_clipeditor_region()
    if not region: return

    resize(pg, movieclip, viewport)

    # opengl part

    act_tex = Buffer(GL_INT, 1)
    glGetIntegerv(GL_TEXTURE_BINDING_2D, act_tex)

    # add window viewport

    winviewport = Buffer(GL_INT, 4)
    glGetIntegerv(GL_VIEWPORT, winviewport)

    viewport[0] += winviewport[0]
    viewport[1] += winviewport[1]

    # dump buffer in texture
    update_image(pg.color_texture, viewport, GL_RGBA, GL_TEXTURE0)

    # run screenshader
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)

    # set identity matrices
    view_setup()

    glUseProgram(pg.program)

    # update uniforms

    # calculate matrixes
    matrix = pg.orientation

    # applied the  calibration matrix
    transformation_matrix = Buffer(GL_FLOAT, (4,4), matrix)

    setup_uniforms(pg.program, pg.color_texture, transformation_matrix)

    draw_rectangle(region, region.width, region.height)

    # restore opengl defaults
    view_reset()

    glUseProgram(0)
    glActiveTexture(act_tex[0])
    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_DEPTH_TEST)
    """
    import blf

    glColor4f(1.0, 1.0, 1.0, 1.0)
    font_id = 0  # XXX, need to find out how best to get this.

    # draw some text
    blf.position(font_id, 15, 30, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Fooooood")
    """

# ############################################################
# Globals
# ############################################################

class PanoramaGlobals:
    is_enabled = False
    handle = None
    buffer_width = -1
    buffer_height = -1
    color_texture = -1
    program = -1
    orientation = [[i for i in range(4)] for j in range(4)]


# ############################################################
# Callbacks
# ############################################################

@persistent
def panorama_tracker_load_pre(dummy):
    panorama_reset(bpy.panorama_globals)


@persistent
def panorama_tracker_load_post(dummy):
    panorama_reset(bpy.panorama_globals)


# ###############################
#  Register / Unregister
# ###############################
def register():
    bpy.app.handlers.load_pre.append(panorama_tracker_load_pre)
    bpy.app.handlers.load_pre.append(panorama_tracker_load_post)

    bpy.panorama_globals = PanoramaGlobals()
    bpy.panorama_globals.handler = bpy.types.SpaceClipEditor.draw_handler_add(draw_panorama_callback_px, (None,), 'WINDOW', 'POST_PIXEL')


def unregister():
    bpy.app.handlers.load_pre.remove(panorama_tracker_load_pre)
    bpy.app.handlers.load_pre.remove(panorama_tracker_load_post)

    bpy.types.SpaceClipEditor.draw_handler_remove(bpy.panorama_globals.handler, 'WINDOW')
