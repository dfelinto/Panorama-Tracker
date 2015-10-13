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
        view_reset,
        view_setup,
        )

from bgl import *

TODO = False

# ###############################
# Utils
# ###############################

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


def draw_rectangle(region, width, height, coordinates=((1,1),(0,1),(0,0),(1,0))):
    verco = []
    for x,y in coordinates:
        co = list(region.view2d.view_to_region(x,y, False))
        co[0] /= float(width)
        co[1] /= float(height)
        verco.append(co)

    glPolygonMode(GL_FRONT_AND_BACK , GL_FILL)
    glEnable(GL_BLEND)
    glBegin(GL_QUADS)
    for i in range(4):
        glColor4f(1.0, 1.0, 0.0, 0.5)
        glVertex2f(verco[i][0], verco[i][1])
    glEnd()
    glDisable(GL_BLEND)


def get_clipeditor_region():
    for area in bpy.context.screen.areas:
        if area.type == 'CLIP_EDITOR':
            for region in area.regions:
                if region.type == 'WINDOW':
                    return region, region.width, region.height

    return None, 0, 0


# ###############################
# Main Drawing Routine
# ###############################

@persistent
def draw_panorama_callback_px(not_used):
    """"""
    movieclip = bpy.context.edit_movieclip
    scene = bpy.context.scene

    if not movieclip: return

    settings = movieclip.panorama_settings
    if not settings.show_preview: return

    tracking = movieclip.tracking.objects[movieclip.tracking.active_object_index]

    region, width, height = get_clipeditor_region()
    if not region: return

    viewport = Buffer(GL_INT, 4)
    glGetIntegerv(GL_VIEWPORT, viewport)

    # set identity matrices
    view_setup()

    frame_current = scene.frame_current
    #coordinates = get_markers_coordinates(tracking, settings, frame_current)
    coordinates=((1,1),(0,1),(0,0),(1,0))
    draw_rectangle(region, width, height, coordinates)

    # restore opengl defaults
    view_reset()

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
    handle = None


# ############################################################
# Callbacks
# ############################################################

@persistent
def panorama_tracker_load_pre(dummy):
    TODO # cleanup


@persistent
def panorama_tracker_load_post(dummy):
    TODO # cleanup


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
