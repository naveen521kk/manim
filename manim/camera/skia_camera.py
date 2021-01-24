"A camera converts the mobjects contained in a Scene into an array of pixels."


__all__ = ["SkiaCamera"]

from cairo import Surface
from .camera import Camera
import skia
import glfw
from ..utils.simple_functions import fdiv
import itertools as it
import numpy as np
from .. import logger


def glfw_context(pw,ph):
    if not glfw.init():
        raise RuntimeError("glfw.init() failed")
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    glfw.window_hint(glfw.STENCIL_BITS, 8)
    window = glfw.create_window(pw,ph, "", None, None)
    glfw.make_context_current(window)


class SkiaCamera(Camera):
    """Skia camera class.

    This inherits from the base Camera Class.
    Replace cairo.
    """

    def __init__(
        self,
        **kwargs,
    ):
        """Initialises the Camera.

        Parameters
        ----------
        background : optional
            What self.background should be, by default None as will be set later.
        **kwargs
            Any local variables to be set.
        """
        # super.__init__(**kwargs)
        super(SkiaCamera, self).__init__(**kwargs)
        #glfw_context(self.pixel_width,self.pixel_height)
        

    def __del__(self):
        glfw.terminate()

    @property
    def pixel_array(self):
        if hasattr(self, "_pixel_array"):
            return self._pixel_array
        else:
            surface = self.skia_surface
            # with surface as context:
            #    context.drawCircle(100, 100, 40, skia.Paint(Color=skia.ColorGREEN))
            # with surface as context:
            #    context.drawCircle(100, 200, 40, skia.Paint(Color=skia.ColorBLUE))
            self._pixel_array = surface.toarray()
            return self._pixel_array

    def reset(self):
        """Resets the camera's pixel array
        to that of the background

        Returns
        -------
        Camera
            The camera object after setting the pixel array.
        """ ""
        if hasattr(self, "_pixel_array"):
            del self._pixel_array
        if hasattr(self, "_skia_surface"):
            del self._skia_surface
        #logger.info("reset")

    def set_pixel_array(self, pixel_array, convert_from_floats=False):
        """Sets the pixel array of the camera to the passed pixel array.

        Parameters
        ----------
        pixel_array : np.array, list, tuple
            The pixel array to convert and then set as the camera's pixel array.
        convert_from_floats : bool, optional
            Whether or not to convert float values to proper RGB values, by default False
        """
        converted_array = self.convert_pixel_array(pixel_array, convert_from_floats)
        if not (
            hasattr(self, "_pixel_array")
            and self._pixel_array.shape == converted_array.shape
        ):
            self._pixel_array = converted_array
        else:
            # Set in place
            self._pixel_array[:, :, :] = converted_array[:, :, :]

    @property
    def skia_surface(self):
        """Returns the cairo context for a pixel array after
        caching it to self.pixel_array_to_cairo_context
        If that array has already been cached, it returns the
        cached version instead.

        Parameters
        ----------
        pixel_array : np.array
            The Pixel array to get the cairo context of.

        Returns
        -------
        skia.Canvas
            The skia canvas of the pixel array.
        """
        if hasattr(self, "_skia_surface"):
            return self._skia_surface
        
        pw = self.pixel_width
        ph = self.pixel_height
        fw = self.frame_width
        fh = self.frame_height
        fc = self.frame_center
        #context = skia.GrDirectContext.MakeGL()
        #info = skia.ImageInfo.MakeN32Premul(pw, ph)
        #surface = skia.Surface.MakeRenderTarget(context, skia.Budgeted.kNo, info)
        surface = skia.Surface(pw, ph)
        assert surface is not None
        self._skia_surface = surface
        self.matrix = skia.Matrix.I().setAffine([fdiv(pw, fw),
                0,
                0,
                -fdiv(ph, fh),
                (pw / 2) - fc[0] * fdiv(pw, fw),
                (ph / 2) + fc[1] * fdiv(ph, fh),])
        #logger.info(self.matrix.asAffine())
        #self._pixel_array = surface.toarray()
        return surface
        # canvas = surface.getCanvas()
        # canvas.scale(pw, ph)
        # canvas.set_matrix(
        #     cairo.Matrix(
        #         fdiv(pw, fw),
        #         0,
        #         0,
        #         -fdiv(ph, fh),
        #         (pw / 2) - fc[0] * fdiv(pw, fw),
        #         (ph / 2) + fc[1] * fdiv(ph, fh),
        #     )
        # )
        # self.cache_skia_canvas(pixel_array, canvas)
        # return canvas

    def prepare_canvas_for_drawing(self, canvas):
        pw = self.pixel_width
        ph = self.pixel_height
        fw = self.frame_width
        fh = self.frame_height
        fc = self.frame_center
        canvas.scale(pw, ph)
        #self.matrix.setScale(pw,ph)
        canvas.setMatrix(self.matrix)
        #canvas.scale(pw/2, ph/2)
        return canvas
    def update_array_from_skia(self):
        self._pixel_array = self.skia_surface.toarray()
    def display_vectorized(self, vmobject):
        """Displays a VMobject in the skia surface.

        Parameters
        ----------
        vmobject : VMobject
            The Vectorized Mobject to display
        canvas : skia.Canvas
            The skia Canvas to use.

        Returns
        -------
        Camera
            The camera object
        """
        
        surface = self.skia_surface
        with surface as canvas:
            paint1 = skia.Paint()
            self.apply_stroke_for_paint(paint1, vmobject,canvas, background=True)
            #self.set_skia_context_path(canvas, vmobject, paint)
            paint2 = skia.Paint()
            self.apply_fill_for_paint(paint2, vmobject, canvas)
            #self.set_skia_context_path(canvas, vmobject, paint)
            paint3 = skia.Paint()
            self.apply_stroke_for_paint(paint3, vmobject, canvas)
            self.set_skia_context_path(canvas, vmobject, paints = [paint1,paint3,paint2])
            self.update_array_from_skia()
        return self

    def set_skia_context_path(self, canvas, vmobject, paints):
        """Sets a path for the cairo context with the vmobject passed

        Parameters
        ----------
        canvas : skia.Canvas
            The cairo context
        vmobject : VMobject
            The VMobject

        Returns
        -------
        Camera
            Camera object after setting cairo_context_path
        """
        canvas = self.prepare_canvas_for_drawing(canvas)
        points = self.transform_points_pre_display(vmobject, vmobject.points)
        if len(points) == 0:
            return
        subpaths = vmobject.gen_subpaths_from_points_2d(points)
        for subpath in subpaths:
            quads = vmobject.gen_cubic_bezier_tuples_from_points(subpath)
            path = skia.PathBuilder()
            #path.setFillType(skia.PathFillType.)
            start = subpath[0]
            path.moveTo(*start[:2])
            for p0, p1, p2, p3 in quads:
                path.cubicTo(*p1[:2],*p2[:2], *p3[:2])
            if vmobject.consider_points_equals_2d(subpath[0], subpath[-1]):
                path.close()
                path_shot = path.snapshot()
                #region = skia.Region()
                #region.setPath(region)
                for paint in paints:
                    #canvas.drawPath(path_shot,paint)
                    canvas.clipPath(path_shot)
                    canvas.drawPaint(paint)
                    


    def set_skia_paint_color(self, paint, rgbas, vmobject) -> skia.Paint:
        """Sets the color of the cairo context

        Parameters
        ----------
        canvas : cairo.Context
            The cairo context
        rgbas : np.ndarray
            The RGBA array with which to color the context.
        vmobject : VMobject
            The VMobject with which to set the color.

        Returns
        -------
        Camera
            The camera object
        """
        if len(rgbas) == 1:
            # Use reversed rgb because cairo surface is
            # encodes it in reverse order
            color_space = skia.ColorSpace.MakeSRGB()
            paint.setColor4f(skia.Color4f(tuple([*rgbas[0][2::-1], rgbas[0][3]])), color_space)
            #paint.setColor(skia.ColorRED)
        else:
            points = vmobject.get_gradient_start_and_end_points()
            points = self.transform_points_pre_display(vmobject, points)
            two_points = list(it.chain(*[point[:2] for point in points]))
            step = 1.0 / (len(rgbas) - 1)
            offsets = list(np.arange(0, 1 + step, step))
            colours = []
            for i in rgbas:
                colours.append(int(skia.Color4f(tuple([*i[2::-1], i[3]]))))
            pat = skia.GradientShader.MakeLinear(
                [skia.Point(*two_points[:2]), skia.Point(*two_points[2:])],
                colours,
                positions=offsets,
            )
            paint.setShader(pat)
        return paint

    def apply_fill_for_paint(self, paint, vmobject, canvas):
        """Fills the context

        Parameters
        ----------
        canvas : cairo.Context
            The cairo context
        vmobject : VMobject
            The VMobject

        Returns
        -------
        Camera
            The camera object.
        """
        #logger.info(self.get_fill_rgbas(vmobject))
        paint.setStyle(skia.Paint.Style.kFill_Style)
        paint = self.set_skia_paint_color(
            paint, self.get_fill_rgbas(vmobject), vmobject
        )
        #self.set_skia_context_path(canvas, vmobject, paint)
        return paint

    def apply_stroke_for_paint(self, paint, vmobject,canvas, background=False):
        """Applies a stroke to the VMobject in the cairo context.

        Parameters
        ----------
        paint : skia.Paint
            The cairo context
        vmobject : VMobject
            The VMobject
        background : bool, optional
            Whether or not to consider the background when applying this
            stroke width, by default False

        Returns
        -------
        Camera
            The camera object with the stroke applied.
        """
        paint.setStyle(skia.Paint.Style.kStroke_Style)
        width = vmobject.get_stroke_width(background)
        if width == 0:
            return paint
        self.set_skia_paint_color(
            paint, self.get_stroke_rgbas(vmobject, background=background), vmobject
        )
        #paint = skia.Paint(AntiAlias=True)
        paint.setStrokeWidth(
            width
            * self.cairo_line_width_multiple
            *
            # This ensures lines have constant width
            # as you zoom in on them.
            (self.frame_width / self.frame_width)
        )
        #self.set_skia_context_path(canvas, vmobject, paint)
        return paint

    def display_multiple_non_background_colored_vmobjects(self, vmobjects, pixel_array):
        """Displays multiple VMobjects in the cairo context, as long as they don't have
        background colors.

        Parameters
        ----------
        vmobjects : list
            list of the VMobjects
        pixel_array : np.ndarray
            The Pixel array to add the VMobjects to.
        """
        for vmobject in vmobjects:
            self.display_vectorized(vmobject)