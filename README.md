Panorama-Tracker
================

addon to help producing a stabilized panorama footage via tracking.

How to use it?
 1. add two markers and track them across the frames
 2. select the track you want to use as the pivot/stable point/focus
 3. click on "Set Focus Track"
 4. select the track you want to use as a reference for stability (so the relation between both points remain the same)
 5. click on "Set Target Track"
 6. click on "Panorama Camera"
 7. that's all (as in, you can render out the stabilized panorama).
 
If you change your camera from Panorama to Perspective, you can see that the 3d cursor is always on the "Focus" marker
By default the frame you are when you select "Panorama Camera" is the one that will be used as reference.
That means if you render that frame the result you get is the same from the original footage.
If you click again in "Panorama Camera" in a different frame you will get a new reference frame.
 
If your resulting panorama is upside down click on "Panorama Camera" again to fix it.

* * *

It was recently posted on Blender Network an article about the making of this addon. It also showcases how to use it:
http://www.blendernetwork.org/blog/success-story-by-sebastian-koenig

You can also access the video directly via:
https://vimeo.com/75889844
