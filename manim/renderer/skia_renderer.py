import itertools as it
import typing

import numpy as np
from numpy.lib.arraysetops import isin
import skia
from PIL import Image
from scipy.spatial.distance import pdist

from .. import config, logger
from ..constants import ORIGIN, TAU
from ..mobject.mobject import Mobject
from ..mobject.types.image_mobject import AbstractImageMobject
from ..mobject.types.point_cloud_mobject import PMobject
from ..mobject.types.vectorized_mobject import VMobject
from ..scene.scene_file_writer import SceneFileWriter
from ..utils.color import Colors, color_to_rgba
from ..utils.exceptions import EndSceneEarlyException
from ..utils.family import extract_mobject_family_members
from ..utils.hashing import get_hash_from_play_call
from ..utils.iterables import list_difference_update, list_update
from ..utils.simple_functions import fdiv
from ..utils.space_ops import angle_of_vector
import operator as op

if typing.TYPE_CHECKING:
    from ..scene.scene import Scene


class SkiaRenderer:
    """A renderer using Skia.

    num_plays : Number of play() functions in the scene.
    time: time elapsed since initialisation of scene.
    """

    def __init__(self, skip_animations: bool = False, **kwargs):
        # All of the following are set to EITHER the value passed via kwargs,
        # OR the value stored in the global config dict at the time of
        # _instance construction_.
        self.file_writer = None
        self.camera = SkiaCamera(self)
        self._original_skipping_status = self.skip_animations = skip_animations
        self.animations_hashes = []
        self.num_plays = self.time = 0
        self.static_image = None
        self.setup_skia()

    def init_scene(self, scene: "Scene"):
        self.file_writer = SceneFileWriter(
            self,
            scene.__class__.__name__,
        )

    def play(self, scene: "Scene", *args, **kwargs):
        # Reset skip_animations to the original state.
        # Needed when rendering only some animations, and skipping others.
        self.skip_animations = self._original_skipping_status
        self.update_skipping_status()

        scene.compile_animation_data(*args, **kwargs)

        if self.skip_animations:
            logger.debug(f"Skipping animation {self.num_plays}")
            hash_current_animation = None
        else:
            if config["disable_caching"]:
                logger.info("Caching disabled.")
                hash_current_animation = f"uncached_{self.num_plays:05}"
            else:
                hash_current_animation = get_hash_from_play_call(
                    scene, self.camera, scene.animations, scene.mobjects
                )
                if self.file_writer.is_already_cached(hash_current_animation):
                    logger.info(
                        f"Animation {self.num_plays} : Using cached data (hash : %(hash_current_animation)s)",
                        {"hash_current_animation": hash_current_animation},
                    )
                    self.skip_animations = True
        # adding None as a partial movie file will make file_writer ignore the latter.
        self.file_writer.add_partial_movie_file(hash_current_animation)
        self.animations_hashes.append(hash_current_animation)
        logger.debug(
            "List of the first few animation hashes of the scene: %(h)s",
            {"h": str(self.animations_hashes[:5])},
        )

        # Save a static image, to avoid rendering non moving objects.
        self.static_image = self.save_static_frame_data(scene, scene.static_mobjects)

        self.file_writer.begin_animation(not self.skip_animations)
        scene.begin_animations()
        if scene.is_current_animation_frozen_frame():
            self.update_frame(scene)
            # self.duration stands for the total run time of all the animations.
            # In this case, as there is only a wait, it will be the length of the wait.
            self.freeze_current_frame(scene.duration)
        else:
            scene.play_internal()
        self.file_writer.end_animation(not self.skip_animations)

        self.num_plays += 1

    def update_frame(
        self,
        scene: "Scene",
        mobjects: typing.List[Mobject] = None,
        include_submobjects: bool = True,
        ignore_skipping: bool = True,
        **kwargs,
    ):
        """Update the frame.
        Parameters
        ----------
        mobjects: list, optional
            list of mobjects
        background: np.ndarray, optional
            Pixel Array for Background.
        include_submobjects: bool, optional
        ignore_skipping : bool, optional
        **kwargs
        """
        if self.skip_animations and not ignore_skipping:
            return
        if mobjects is None:
            mobjects = list_update(
                scene.mobjects,
                scene.foreground_mobjects,
            )
        if self.static_image is not None:
            self.set_frame_to_background(self.static_image)
        else:
            self.camera.reset()

        kwargs["include_submobjects"] = include_submobjects
        self.capture_mobjects(mobjects, **kwargs)

    def render(
        self, scene: "Scene", time: int, moving_mobjects: typing.List[Mobject]
    ) -> None:
        self.update_frame(scene, moving_mobjects)
        self.add_frame(self.get_frame())

    def get_frame(self) -> np.ndarray:
        """
        Gets the current frame as NumPy array.
        Returns
        -------
        np.array
            NumPy array of pixel values of each pixel in screen.
            The shape of the array is height x width x 3
        """
        return np.array(self._surface.toarray())

    def add_frame(self, frame, num_frames=1) -> None:
        """
        Adds a frame to the video_file_stream
        Parameters
        ----------
        frame : numpy.ndarray
            The frame to add, as a pixel array.
        num_frames: int
            The number of times to add frame.
        """
        dt = 1 / self.camera.frame_rate
        self.time += num_frames * dt
        if self.skip_animations:
            return
        for _ in range(num_frames):
            self.file_writer.write_frame(frame)

    def freeze_current_frame(self, duration: float) -> None:
        """Adds a static frame to the movie for a given duration. The static frame is the current frame.
        Parameters
        ----------
        duration : float
            [description]
        """
        dt = 1 / self.camera.frame_rate
        self.add_frame(
            self.get_frame(),
            num_frames=int(duration / dt),
        )

    def show_frame(self) -> None:
        """
        Opens the current frame in the Default Image Viewer
        of your system.
        """
        self.update_frame(ignore_skipping=True)
        self.get_image().show()

    def save_static_frame_data(
        self, scene: "Scene", static_mobjects: typing.Iterable[Mobject]
    ) -> np.ndarray:
        """Compute and save the static frame, that will be reused at each frame to avoid to unecesseraly computer
        static mobjects.
        Parameters
        ----------
        scene : Scene
            The scene played.
        static_mobjects : typing.Iterable[Mobject]
            Static mobjects of the scene. If None, self.static_image is set to None
        Returns
        -------
        typing.Iterable[Mobject]
            the static image computed.
        """
        if not static_mobjects:
            self.static_image = None
            return
        self.update_frame(scene, mobjects=static_mobjects)
        self.static_image = self.get_frame()
        return self.static_image

    def update_skipping_status(self):
        """
        This method is used internally to check if the current
        animation needs to be skipped or not. It also checks if
        the number of animations that were played correspond to
        the number of animations that need to be played, and
        raises an EndSceneEarlyException if they don't correspond.
        """
        if config["save_last_frame"]:
            self.skip_animations = True
        if config["from_animation_number"]:
            if self.num_plays < config["from_animation_number"]:
                self.skip_animations = True
        if config["upto_animation_number"]:
            if self.num_plays > config["upto_animation_number"]:
                self.skip_animations = True
                raise EndSceneEarlyException()

    def get_image(self) -> Image:
        image = skia.Surface.makeImageSnapshot(self._surface)
        return Image.fromarray(image.toarray())

    def scene_finished(self, scene: "Scene"):
        # If no animations in scene, render an image instead
        if self.num_plays:
            self.file_writer.finish()
        elif config.write_to_movie:
            config.save_last_frame = True
            config.write_to_movie = False
        else:
            self.update_frame(scene)

        if config["save_last_frame"]:
            self.update_frame(scene)
            self.file_writer.save_final_image(self.get_image())

    # Main methods with working with skia is from here.

    def setup_skia(self):
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

        pw = self.camera.pixel_width
        ph = self.camera.pixel_height
        fw = self.camera.frame_width
        fh = self.camera.frame_height
        fc = self.camera.frame_center
        # context = skia.GrDirectContext.MakeGL()
        # info = skia.ImageInfo.MakeN32Premul(pw, ph)
        # surface = skia.Surface.MakeRenderTarget(context, skia.Budgeted.kNo, info)
        surface = skia.Surface(pw, ph)
        assert surface is not None
        self._surface = surface
        self._canvas = surface.getCanvas()
        
        self._scale_x = fdiv(pw, fw)
        self._skew_x = 0
        self._translate_x = 0
        self._skew_y = -fdiv(ph, fh)
        self._scale_y = (pw / 2) - fc[0] * fdiv(pw, fw)
        self._translate_y = (ph / 2) + fc[1] * fdiv(ph, fh)
        self._matrix = skia.Matrix.I().setAffine(
            [
                self._scale_x,
                self._skew_x,
                self._translate_x,
                self._skew_y,
                self._scale_y,
                self._translate_y,
            ]
        )
        # logger.info(self.matrix.asAffine())
        # self._pixel_array = surface.toarray()
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

    def set_frame_to_background(self, background: np.ndarray):
        canvas = self._canvas
        image = skia.Image.fromarray(background)
        canvas.drawImage(image, 0, 0)  # skia.Image, left, top

    # def capture_mobject(self, mobject: Mobject, **kwargs) -> None:
    #     """Capture one :class:`~Mobject`.

    #     Parameters
    #     ----------
    #     mobject : Mobject
    #         The :class:`Mobject`
    #     """
    #     return self.capture_mobjects([mobject], **kwargs)

    def capture_mobjects(self, mobjects: typing.List[Mobject], **kwargs) -> None:
        """Capture mobjects by printing them on :attr:`pixel_array`.
        This is the essential function that converts the contents of a Scene
        into an array, which is then converted to an image or video.
        Parameters
        ----------
        mobjects : :class:`~.Mobject`
            Mobjects to capture.
        kwargs : Any
            Keyword arguments to be passed to :meth:`get_mobjects_to_display`.
        Notes
        -----
        For a list of classes that can currently be rendered, see :meth:`display_funcs`.
        """
        # The mobjects will be processed in batches (or runs) of mobjects of
        # the same type.  That is, if the list mobjects contains objects of
        # types [VMobject, VMobject, VMobject, PMobject, PMobject, VMobject],
        # then they will be captured in three batches: [VMobject, VMobject,
        # VMobject], [PMobject, PMobject], and [VMobject].  This must be done
        # without altering their order.  it.groupby computes exactly this
        # partition while at the same time preserving order.
        mobjects = self.get_mobjects_to_display(mobjects, **kwargs)
        for group_type, group in it.groupby(mobjects, self.type_or_raise):
            self.display_funcs[group_type](list(group))

    def get_mobjects_to_display(
        self,
        mobjects: typing.List[Mobject],
        include_submobjects: bool = True,
        excluded_mobjects: typing.Optional[typing.List[Mobject]] = None,
    ) -> typing.List[Mobject]:
        """Used to get the list of mobjects to display
        with the camera.
        Parameters
        ----------
        mobjects
            The Mobjects
        include_submobjects
            Whether or not to include the submobjects of mobjects, by default True
        excluded_mobjects
            Any mobjects to exclude, by default None
        Returns
        -------
        list
            list of mobjects
        """
        use_z_index = self.camera.use_z_index
        if include_submobjects:
            mobjects = extract_mobject_family_members(
                mobjects,
                use_z_index=use_z_index,
                only_those_with_points=True,
            )
            if excluded_mobjects:
                all_excluded = extract_mobject_family_members(
                    excluded_mobjects,
                    use_z_index=use_z_index,
                )
                mobjects = list_difference_update(mobjects, all_excluded)
        return mobjects

    def type_or_raise(self, mobject):
        """Return the type of mobject, if it is a type that can be rendered.
        If `mobject` is an instance of a class that inherits from a class that
        can be rendered, return the super class.  For example, an instance of a
        Square is also an instance of VMobject, and these can be rendered.
        Therefore, `type_or_raise(Square())` returns True.
        Parameters
        ----------
        mobject : :class:`~.Mobject`
            The object to take the type of.
        Notes
        -----
        For a list of classes that can currently be rendered, see :meth:`display_funcs`.
        Returns
        -------
        Type[:class:`~.Mobject`]
            The type of mobjects, if it can be rendered.
        Raises
        ------
        :exc:`TypeError`
            When mobject is not an instance of a class that can be rendered.
        """
        self.display_funcs = {
            VMobject: self.display_vectorized_mobjects,
            # PMobject: self.display_point_cloud_mobjects,
            AbstractImageMobject: self.display_image_mobjects,
            Mobject: lambda batch, pa: batch,  # Do nothing
        }
        # We have to check each type in turn because we are dealing with
        # super classes.  For example, if square = Square(), then
        # type(square) != VMobject, but isinstance(square, VMobject) == True.
        for _type in self.display_funcs:
            if isinstance(mobject, _type):
                return _type
        else:
            raise TypeError(f"Displaying an object of class {_type} is not supported")

    def transform_points_pre_display(
        self, mobject: Mobject, points: np.ndarray
    ):  # TODO: Write more detailed docstrings for this method.
        # NOTE: There seems to be an unused argument `mobject`.

        # Subclasses (like ThreeDCamera) may want to
        # adjust points further before they're shown
        if not np.all(np.isfinite(points)):
            # TODO, print some kind of warning about
            # mobject having invalid points?
            points = np.zeros((1, 3))
        return points

    def points_to_pixel_coords(self, mobject: Mobject, points: np.ndarray):
        points = self.transform_points_pre_display(mobject, points)
        shifted_points = points - self.camera.frame_center

        result: np.ndarray = np.zeros((len(points), 2))
        pixel_height = self.camera.pixel_height
        pixel_width = self.camera.pixel_width
        frame_height = self.camera.frame_height
        frame_width = self.camera.frame_width
        width_mult = pixel_width / frame_width
        width_add = pixel_width / 2
        height_mult = pixel_height / frame_height
        height_add = pixel_height / 2
        # Flip on y-axis as you go
        height_mult *= -1

        result[:, 0] = shifted_points[:, 0] * width_mult + width_add
        result[:, 1] = shifted_points[:, 1] * height_mult + height_add
        return result.astype("int")

    def display_image_mobjects(
        self,
        image_mobject: typing.Union[
            typing.List[AbstractImageMobject], AbstractImageMobject
        ],
    ):
        """Displays multiple image mobjects by modifying the passed pixel_array.
        Parameters
        ----------
        image_mobjects : list
            list of ImageMobjects
        """
        if isinstance(image_mobject, AbstractImageMobject):
            corner_coords = self.points_to_pixel_coords(image_mobject, image_mobject.points)
            ul_coords, ur_coords, dl_coords = corner_coords
            right_vect = ur_coords - ul_coords
            down_vect = dl_coords - ul_coords
            center_coords = ul_coords + (right_vect + down_vect) / 2

            sub_image = Image.fromarray(image_mobject.get_pixel_array(), mode="RGBA")

            # Reshape
            pixel_width = max(int(pdist([ul_coords, ur_coords])), 1)
            pixel_height = max(int(pdist([ul_coords, dl_coords])), 1)
            sub_image = sub_image.resize(
                (pixel_width, pixel_height), resample=image_mobject.resampling_algorithm
            )

            # Rotate
            angle = angle_of_vector(right_vect)
            adjusted_angle = -int(360 * angle / TAU)
            if adjusted_angle != 0:
                sub_image = sub_image.rotate(
                    adjusted_angle, resample=image_mobject.resampling_algorithm, expand=1
                )

            # TODO, there is no accounting for a shear...

            # Paste into an image as large as the camera's pixel array
            full_image = Image.fromarray(
                np.zeros((self.camera.pixel_height, self.camera.pixel_width)), mode="RGBA"
            )
            new_ul_coords = center_coords - np.array(sub_image.size) / 2
            new_ul_coords = new_ul_coords.astype(int)
            full_image.paste(
                sub_image,
                box=(
                    new_ul_coords[0],
                    new_ul_coords[1],
                    new_ul_coords[0] + sub_image.size[0],
                    new_ul_coords[1] + sub_image.size[1],
                ),
            )
            canvas = self._canvas
            image = skia.Image.fromarray(np.array(full_image))
            canvas.drawImage(image, 0, 0)
        else:
            for sub_image_mobject in image_mobject:
                self.display_image_mobjects(sub_image_mobject)

    def display_vectorized_mobjects(
        self,
        vmobject: typing.Union[typing.List[VMobject], VMobject],
    ):
        if isinstance(vmobject, VMobject):
            batch_file_pairs = it.groupby(vmobject, lambda vm: vm.background_image_file)
            for file_name, batch in batch_file_pairs:
                if file_name:
                    raise NotImplementedError(
                        "display_multiple_background_colored_vmobjects"
                    )
                    # self.display_multiple_background_colored_vmobjects(batch)
                else:
                    for each_vmobject in batch:
                        canvas = self._canvas
                        paint1 = skia.Paint()
                        self.apply_stroke_for_paint(
                            paint1, each_vmobject, canvas, background=True
                        )
                        # self.set_skia_context_path(canvas, vmobject, paint)
                        paint2 = skia.Paint()
                        paint2.setStyle(skia.Paint.Style.kFill_Style)
                        self.set_skia_paint_color(
                            paint2, each_vmobject.get_fill_rgbas(), each_vmobject
                        )
                        # self.set_skia_context_path(canvas, vmobject, paint)
                        paint3 = skia.Paint()
                        paint3.setAntiAlias(True)
                        self.apply_stroke_for_paint(paint3, each_vmobject, canvas)
                        self.set_skia_context_path(
                            canvas, each_vmobject, paints=[paint1, paint2, paint3]
                        )
                        return self
        else:
            for sub_vm_object in vmobject:
                self.display_vectorized_mobjects(sub_vm_object)

    def set_skia_context_path(self, canvas: skia.Canvas, vmobject: VMobject, paints: typing.Sequence[skia.Paint]):
        #canvas = self.prepare_canvas_for_drawing(canvas)
        self._canvas.setMatrix(self._matrix)
        points = self.transform_points_pre_display(vmobject, vmobject.points)
        if len(points) == 0:
            return
        subpaths = vmobject.gen_subpaths_from_points_2d(points)
        for subpath in subpaths:
            quads = vmobject.gen_cubic_bezier_tuples_from_points(subpath)
            path = skia.Path()
            #path.setFillType(skia.PathFillType.)
            start = subpath[0]
            path.moveTo(*start[:2])
            for p0, p1, p2, p3 in quads:
                path.cubicTo(*p1[:2],*p2[:2], *p3[:2])
            if vmobject.consider_points_equals_2d(subpath[0], subpath[-1]):
                path.close()
                #path_shot = path.snapshot()
                #region = skia.Region()
                #region.setPath(region)
                for paint in paints:
                    canvas.drawPath(path,paint)
                    #canvas.clipPath(path)
                    #canvas.drawPaint(paint)
        self._canvas.setMatrix(skia.Matrix.I())
    def set_skia_paint_color(
        self, paint: skia.Paint, rgbas: np.ndarray, vmobject: VMobject
    ):
        if len(rgbas) == 1:
            # Use reversed rgb because cairo surface is
            # encodes it in reverse order
            color_space = skia.ColorSpace.MakeSRGB()
            paint.setColor4f(
                skia.Color4f(tuple([*rgbas[0][2::-1], rgbas[0][3]])), color_space
            )
            # paint.setColor(skia.ColorRED)
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

    def apply_stroke_for_paint(self, paint: skia.Paint, vmobject: VMobject,canvas: skia.Canvas, background: bool=False):
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
            paint, vmobject.get_stroke_rgbas(background=background), vmobject
        )
        #paint = skia.Paint(AntiAlias=True)
        paint.setStrokeWidth(
            width
            * self.camera.line_width_multiple
            *
            # This ensures lines have constant width
            # as you zoom in on them.
            #(self.frame_width / self.frame_width)
            (self.camera.frame_width / self.camera.frame_width)
        )
        #self.set_skia_context_path(canvas, vmobject, paint)
        #return paint

    # TODO: later
    # def display_point_cloud_mobjects(
    #     self,
    #     pmobject: typing.Union[typing.List[PMobject], PMobject],
    # ):
    #     if isinstance(pmobject,PMobject):
    #         points = pmobject.points
    #         rgbas = pmobject.rgbas
    #         thickness = self.adjusted_thickness(pmobject.stroke_width)
    #         if len(points) == 0:
    #             return
    #         pixel_coords = self.points_to_pixel_coords(pmobject, points)
    #         pixel_coords = self.thickened_coordinates(pixel_coords, thickness)
    #         rgba_len = pixel_array.shape[2]

    #         rgbas = (self.rgb_max_val * rgbas).astype(self.pixel_array_dtype)
    #         target_len = len(pixel_coords)
    #         factor = target_len // len(rgbas)
    #         rgbas = np.array([rgbas] * factor).reshape((target_len, rgba_len))

    #         on_screen_indices = self.on_screen_pixels(pixel_coords)
    #         pixel_coords = pixel_coords[on_screen_indices]
    #         rgbas = rgbas[on_screen_indices]

    #         ph = self.pixel_height
    #         pw = self.pixel_width

    #         flattener = np.array([1, pw], dtype="int")
    #         flattener = flattener.reshape((2, 1))
    #         indices = np.dot(pixel_coords, flattener)[:, 0]
    #         indices = indices.astype("int")

    #         new_pa = pixel_array.reshape((ph * pw, rgba_len))
    #         new_pa[indices] = rgbas
    #         pixel_array[:, :] = new_pa.reshape((ph, pw, rgba_len))
    #     else:
    #         for sub_pm_object in pmobject:
    #             self.display_point_cloud_mobjects(pmobject)

    # def adjusted_thickness(self, thickness: typing.Union[int,float]):
    #     """
    #     Parameters
    #     ----------
    #         thickness : int, float
    #     Returns
    #     -------
    #     float
    #     """
    #     # TODO: This seems...unsystematic
    #     big_sum = op.add(config["pixel_height"], config["pixel_width"])
    #     this_sum = op.add(self.pixel_height, self.pixel_width)
    #     factor = fdiv(big_sum, this_sum)
    #     return 1 + (thickness - 1) / factor

    # def thickened_coordinates(self, pixel_coords: np.ndarray, thickness: typing.Union[int,float]):
    #     """Returns thickened coordinates for a passed array of pixel coords and
    #     a thickness to thicken by.
    #     Parameters
    #     ----------
    #     pixel_coords : np.array
    #         Pixel coordinates
    #     thickness : int, float
    #         Thickness
    #     Returns
    #     -------
    #     np.array
    #         Array of thickened pixel coords.
    #     """
    #     nudges = self.get_thickening_nudges(thickness)
    #     pixel_coords = np.array([pixel_coords + nudge for nudge in nudges])
    #     size = pixel_coords.size
    #     return pixel_coords.reshape((size // 2, 2))


class SkiaCamera:
    def __init__(
        self,
        renderer: SkiaRenderer,
        frame_center: np.ndarray = ORIGIN,
        background: typing.Optional[np.ndarray] = None,
        background_color: typing.Optional[Colors] = None,
        line_width_multiple: float = 0.01
    ):
        self.use_z_index = True

        self.pixel_height = config["pixel_height"]
        self.pixel_width = config["pixel_width"]
        self.frame_height = config["frame_height"]
        self.frame_width = config["frame_width"]
        self.frame_rate = config["frame_rate"]
        self.frame_center = frame_center

        self.background = background
        self.background_color = (
            background_color if background_color else config["background_color"]
        )
        self.renderer = renderer
        self.line_width_multiple = line_width_multiple

    def reset(self):
        canvas = self.renderer._canvas
        color = skia.Color4f(*color_to_rgba(self.background_color))
        canvas.clear(color)
        if self.background:
            image = skia.Image.fromarray(self.background)
            canvas.drawImage(image, 0, 0)
