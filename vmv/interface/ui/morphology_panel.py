####################################################################################################
# Copyright (c) 2019, EPFL / Blue Brain Project
#               Marwan Abdellah <marwan.abdellah@epfl.ch>
#
# This file is part of VessMorphoVis <https://github.com/BlueBrain/VessMorphoVis>
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, version 3 of the License.
#
# This Blender-based tool is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <http://www.gnu.org/licenses/>.
####################################################################################################

# System import
import copy

# Blender imports
import bpy
from mathutils import Vector

# Internal imports
import vmv
import vmv.enums
import vmv.file
import vmv.builders
import vmv.skeleton
import vmv.utilities


####################################################################################################
# @VMVMorphologyPanel
####################################################################################################
class VMVMorphologyPanel(bpy.types.Panel):
    """Morphology reconstruction panel"""

    ################################################################################################
    # Panel parameters
    ################################################################################################

    bl_label = 'Morphology Reconstruction'
    bl_idname = "OBJECT_PT_MorphologyReconstruction"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = 'VessMorphoVis'
    bl_options = {'DEFAULT_CLOSED'}

    ################################################################################################
    # Panel options
    ################################################################################################

    # Center morphology at the origin
    bpy.types.Scene.CenterMorphology = bpy.props.BoolProperty(
        name="Center Morphology at Origin",
        description="Center the loaded morphology skeleton at the origin to make it easy to "
                    "navigate and visualize it",
        default=True)

    # Progressive reconstruction
    bpy.types.Scene.ProgressiveReconstruction = bpy.props.BoolProperty(
        name="Progressive Reconstruction",
        description="Show the sequence of reconstructing the morphology interactively. "
                    "This option might be slow for large datasets that have more than 10000 "
                    "morphological samples",
        default=False)

    # Adaptive resampling
    bpy.types.Scene.AdaptiveResampling = bpy.props.BoolProperty(
        name="Adaptive Resampling",
        description="Resample the morphology skeleton adaptively to reduce the number of drawn "
                    "samples while preserving the structure of the morphology",
        default=False)

    # Reconstruction method
    bpy.types.Scene.ReconstructionMethod = bpy.props.EnumProperty(
        items=[(vmv.enums.Skeletonization.Method.DISCONNECTED_SEGMENTS,
                'Disconnected Segments',
                "Each segment is an independent object (this approach is time consuming)"),
               (vmv.enums.Skeletonization.Method.DISCONNECTED_SECTIONS,
                'Disconnected Sections',
                "Each section is an independent object"),
               (vmv.enums.Skeletonization.Method.CONNECTED_SECTIONS,
                'Connected Sections',
                "The sections of a single arbor are connected together"),
               (vmv.enums.Skeletonization.Method.CONNECTED_SKELETON,
                'Connected Skeleton',
                "The morphology is reconstructed as a skeleton")],
        name="Method",
        default=vmv.enums.Skeletonization.Method.DISCONNECTED_SECTIONS)

    # Rendering resolution
    bpy.types.Scene.MorphologyRenderingResolution = bpy.props.EnumProperty(
        items=[(vmv.enums.Meshing.Rendering.Resolution.FIXED_RESOLUTION,
                'Fixed',
                'Renders an image of the mesh at a specific resolution given by the user'),
               (vmv.enums.Meshing.Rendering.Resolution.TO_SCALE,
                'To Scale',
                'Renders an image of the mesh at factor of the exact scale')],
        name='Type',
        default=vmv.enums.Meshing.Rendering.Resolution.FIXED_RESOLUTION)

    # Rendering views
    bpy.types.Scene.MorphologyRenderingViews = bpy.props.EnumProperty(
        items=[(vmv.enums.Camera.View.FRONT,
                'Front View',
                'Render the front view of the mesh'),
               (vmv.enums.Camera.View.SIDE,
                'Side View',
                'Renders the side view of the mesh'),
               (vmv.enums.Camera.View.TOP,
                'Top View',
                'Renders the top view of the mesh')],
        name='View', default=vmv.enums.Camera.View.FRONT)

    # Exported mesh file formats
    bpy.types.Scene.ExportedMorphologyFormat = bpy.props.EnumProperty(
        items=[(vmv.enums.Meshing.ExportFormat.PLY,
                'Stanford (.ply)',
                'Export the mesh to a .ply file'),
               (vmv.enums.Meshing.ExportFormat.OBJ,
                'Wavefront(.obj)',
                'Export the mesh to a .obj file'),
               (vmv.enums.Meshing.ExportFormat.STL,
                'Stereolithography CAD (.stl)',
                'Export the mesh to an .stl file'),
               (vmv.enums.Meshing.ExportFormat.OFF,
                'Object File Format (.off)',
                'Export the mesh to an .off file'),
               (vmv.enums.Meshing.ExportFormat.BLEND,
                'Blender File (.blend)',
                'Export the mesh as a .blend file')],
        name='Format', default=vmv.enums.Meshing.ExportFormat.PLY)

    # Skeleton style
    #bpy.types.Scene.SkeletonStyle = bpy.props.EnumProperty(
    #    items=vmv.enums.Skeletonization.Style.,
    #    name="Skeleton Style",
    #    default=vmv.enums.Skeletonization.Style.ORIGINAL)

    # Branching, is it based on angles or radii
    bpy.types.Scene.MorphologyBranching = bpy.props.EnumProperty(
        items=[(vmv.enums.Skeletonization.Branching.ANGLES,
                'Angles',
                'Make the branching based on the angles at branching points'),
               (vmv.enums.Skeletonization.Branching.RADII,
                'Radii',
                'Make the branching based on the radii of the children at the branching points')],
        name='Branching Style',
        default=vmv.enums.Skeletonization.Branching.RADII)

    # Mesh materials
    bpy.types.Scene.MorphologyMaterial = bpy.props.EnumProperty(
        items=vmv.enums.Shading.MATERIAL_ITEMS,
        name="Material",
        default=vmv.enums.Shading.LAMBERT_WARD)

    # Mesh color
    bpy.types.Scene.MorphologyColor = bpy.props.FloatVectorProperty(
        name="Morphology Color", subtype='COLOR',
        default=vmv.consts.Color.GRAY, min=0.0, max=1.0,
        description="The color of the reconstructed morphology")

    # 360 rendering progress bar
    bpy.types.Scene.MorphologyRenderingProgress = bpy.props.IntProperty(
        name="Rendering Progress",
        default=0, min=0, max=100, subtype='PERCENTAGE')

    # Image resolution
    bpy.types.Scene.MorphologyFrameResolution = bpy.props.IntProperty(
        name='Resolution',
        description='The resolution of the image generated from rendering the morphology',
        default=512, min=128, max=1024 * 10)

    # Frame scale factor 'for rendering to scale option '
    bpy.types.Scene.MorphologyFrameScaleFactor = bpy.props.FloatProperty(
        name="Scale", default=1.0, min=1.0, max=100.0,
        description="The scale factor for rendering a morphology to scale")

    # Reconstruction progress bar
    bpy.types.Scene.ReconstructionProgress = bpy.props.IntProperty(
        name="Progress",
        default=0, min=0, max=100, subtype='PERCENTAGE')

    # Tube quality
    bpy.types.Scene.TubeQuality = bpy.props.IntProperty(
        name="Sides",
        description="Number of sides of the cross-section of each segment along the drawn tube."
                    "The minimum is 4, maximum 128 and default is 8. High value is required for "
                    "closeups and low value is sufficient for far-away visualizations",
        default=8, min=4, max=128)

    # Section radius
    bpy.types.Scene.SectionsRadii = bpy.props.EnumProperty(
        items=[(vmv.enums.Skeletonization.Radii.AS_SPECIFIED,
                'As Specified in Morphology',
                "Use the cross-sectional radii as reported in the morphology file"),
               (vmv.enums.Skeletonization.Radii.FIXED,
                'At a Fixed Radii',
                "Set all the tubes to a fixed radius"),
               (vmv.enums.Skeletonization.Radii.SCALED,
                'With Scale Factor',
                "Scale all the tubes using a specified scale factor")],
        name="Radii",
        default=vmv.enums.Skeletonization.Radii.AS_SPECIFIED)

    # Fixed section radius value
    bpy.types.Scene.FixedRadiusValue = bpy.props.FloatProperty(
        name="Value (micron)",
        description="The value of the fixed radius in microns between (0.05 and 5.0)",
        default=1.0, min=0.05, max=5.0)

    # Tubes radius scale value
    bpy.types.Scene.RadiusScaleValue = bpy.props.FloatProperty(
        name="Scale",
        description="A scale factor for scaling the radii of the tubes between (0.01 and 5.0)",
        default=1.0, min=0.01, max=5.0)




    # Material
    bpy.types.Scene.MorphologyMaterial = bpy.props.EnumProperty(
        items=vmv.enums.Shading.MATERIAL_ITEMS,
        name="Material",
        default=vmv.enums.Shading.LAMBERT_WARD)

    # Color each component
    bpy.types.Scene.ColorComponents = bpy.props.BoolProperty(
        name="Color Components",
        description="Each component of the morphology will be assigned a different random color",
        default=False)

    # Color the components using black and white alternatives
    bpy.types.Scene.ColorComponentsBlackAndWhite = bpy.props.BoolProperty(
        name="Black / White",
        description="Each component of the morphology will be assigned a either black or white",
        default=False)

    # A homogeneous color for all the objects of the morphology
    bpy.types.Scene.MorphologyColor = bpy.props.FloatVectorProperty(
        name="Surface Color",
        subtype='COLOR', default=vmv.consts.Color.GRAY, min=0.0, max=1.0,
        description="The color of the reconstructed morphology")

    ################################################################################################
    # @draw_mesh_reconstruction_options
    ################################################################################################
    def draw_morphology_reconstruction_options(self,
                                               context):
        """Draws the morphology reconstruction options.

        :param context:
            Context.
        """

        # Skeleton meshing options
        skeleton_meshing_options_row = self.layout.row()
        skeleton_meshing_options_row.label(
            text='Morphology Reconstruction Options:', icon='SURFACE_DATA')

        # Morphology reconstruction techniques option
        morphology_reconstruction_row = self.layout.row()
        morphology_reconstruction_row.prop(
            context.scene, 'ReconstructionMethod', icon='FORCE_CURVE')
        vmv.interface.ui.ui_options.morphology.reconstruction_method = \
            context.scene.ReconstructionMethod

        # Sections radii option
        sections_radii_row = self.layout.row()
        sections_radii_row.prop(context.scene, 'SectionsRadii', icon='SURFACE_NCURVE')

        # Radii as specified in the morphology file
        if context.scene.SectionsRadii == vmv.enums.Skeletonization.Radii.AS_SPECIFIED:

            # Pass options from UI to system
            vmv.interface.ui.ui_options.morphology.radii = \
                vmv.enums.Skeletonization.Radii.AS_SPECIFIED
            vmv.interface.ui.ui_options.morphology.scale_sections_radii = False
            vmv.interface.ui.ui_options.morphology.unify_sections_radii = False
            vmv.interface.ui.ui_options.morphology.sections_radii_scale = 1.0

        # Fixed diameter
        elif context.scene.SectionsRadii == vmv.enums.Skeletonization.Radii.FIXED:

            fixed_diameter_row = self.layout.row()
            fixed_diameter_row.label(text='Fixed Radius Value:')
            fixed_diameter_row.prop(context.scene, 'FixedRadiusValue')

            # Pass options from UI to system
            vmv.interface.ui.ui_options.morphology.radii = vmv.enums.Skeletonization.Radii.FIXED
            vmv.interface.ui.ui_options.morphology.scale_sections_radii = False
            vmv.interface.ui.ui_options.morphology.unify_sections_radii = True
            vmv.interface.ui.ui_options.morphology.sections_fixed_radii_value = \
                context.scene.FixedRadiusValue

        # Scaled diameter
        elif context.scene.SectionsRadii == vmv.enums.Skeletonization.Radii.SCALED:

            scaled_diameter_row = self.layout.row()
            scaled_diameter_row.label(text='Radius Scale Factor:')
            scaled_diameter_row.prop(context.scene, 'RadiusScaleValue')

            # Pass options from UI to system
            vmv.interface.ui.ui_options.morphology.radii = vmv.enums.Skeletonization.Radii.SCALED
            vmv.interface.ui.ui_options.morphology.unify_sections_radii = False
            vmv.interface.ui.ui_options.morphology.scale_sections_radii = True
            vmv.interface.ui.ui_options.morphology.sections_radii_scale = \
                context.scene.RadiusScaleValue

        else:
            vmv.logger.log('ERROR')

        # Tube quality
        tube_quality_row = self.layout.row()
        tube_quality_row.label(text='Tube Quality:')
        tube_quality_row.prop(context.scene, 'TubeQuality')
        vmv.interface.ui.ui_options.morphology.bevel_object_sides = context.scene.TubeQuality

        # Center morphology
        center_morphology_row = self.layout.row()
        center_morphology_row.prop(context.scene, 'CenterMorphology')
        vmv.interface.ui.ui_options.morphology.global_coordinates = \
            not context.scene.CenterMorphology

        # Progressive reconstruction
        progressive_reconstruction_row = self.layout.row()
        progressive_reconstruction_row.prop(context.scene, 'ProgressiveReconstruction')

        # Adaptive resampling
        adaptive_resampling_row = self.layout.row()
        adaptive_resampling_row.prop(context.scene, 'AdaptiveResampling')
        vmv.interface.ui.ui_options.morphology.adaptive_resampling = \
            context.scene.AdaptiveResampling

        # Morphology reconstruction techniques option
        # skeleton_style_row = self.layout.row()
        # skeleton_style_row.prop(context.scene, 'ArborsStyle', icon='WPAINT_HLT')


        # Morphology branching
        #branching_row = self.layout.row()
        #branching_row.label(text='Branching:')
        #branching_row.prop(context.scene, 'MorphologyBranching', expand=True)
        #vmv.interface.ui.ui_options.morphology.branching = context.scene.MorphologyBranching

        # Arbor quality option
        #arbor_quality_row = self.layout.row()
        #arbor_quality_row.label(text='Arbor Quality:')
        #arbor_quality_row.prop(context.scene, 'ArborQuality')


        # Sections diameters option
        #sections_radii_row = self.layout.row()
        #sections_radii_row.prop(context.scene, 'SectionsRadii', icon='SURFACE_NCURVE')


    ################################################################################################
    # @draw_morphology_color_options
    ################################################################################################
    def draw_morphology_color_options(self, context):
        """Draw the coloring options.

        :param context:
            Context.
        """

        # Get a reference to the layout of the panel
        layout = self.layout

        # Coloring parameters
        colors_row = self.layout.row()
        colors_row.label(text='Colors & Materials:', icon='COLOR')

        # Morphology material
        morphology_material_row = self.layout.row()
        morphology_material_row.prop(context.scene, 'MorphologyMaterial')
        vmv.interface.ui.ui_options.morphology.material = context.scene.MorphologyMaterial

        # Coloring individual components
        color_components_row = layout.row()
        color_components_row.prop(context.scene, 'ColorComponents')
        color_black_white_row = color_components_row.column()
        color_black_white_row.prop(context.scene, 'ColorComponentsBlackAndWhite')
        color_black_white_row.enabled = False

        # Color morphology components based on random coloring or using black-white alternatives
        if context.scene.ColorComponents:

            # Set the color to the COLOR CODE of the random coloring
            vmv.interface.ui.ui_options.morphology.color = Vector((-1, 0, 0))

            # Turn on the option to use black-white coloring scheme
            color_black_white_row.enabled = True

            # If the black-white coloring is enabled
            if context.scene.ColorComponentsBlackAndWhite:

                # Set the color to the COLOR CODE of the random coloring
                vmv.interface.ui.ui_options.morphology.color = Vector((0, -1, 0))

        # Otherwise, select the morphology color from the palette
        else:

            # Morphology color
            color_row = self.layout.row()
            color_row.prop(context.scene, 'MorphologyColor')
            vmv.interface.ui.ui_options.morphology.color = context.scene.MorphologyColor

    ################################################################################################
    # @draw_morphology_reconstruction_button
    ################################################################################################
    def draw_morphology_reconstruction_button(self,
                                              context):
        """Draw the morphology reconstruction button.

        :param context:
            Context.
        """

        # Get a reference to the layout of the panel
        layout = self.layout

        # Mesh quick reconstruction options
        reconstruction_row = self.layout.row()
        reconstruction_row.label(text='Morphology Reconstruction:', icon='PARTICLE_POINT')

        # Morphology reconstruction options
        morphology_reconstruction_row = self.layout.row()
        morphology_reconstruction_row.operator('reconstruct.morphology', icon='MESH_DATA')

        # Reconstruction progress bar
        reconstruction_progress_row = self.layout.row()
        reconstruction_progress_row.prop(context.scene, 'ReconstructionProgress')
        reconstruction_progress_row.enabled = False

    ################################################################################################
    # @draw_morphology_rendering_options
    ################################################################################################
    def draw_morphology_rendering_options(self,
                                          context):
        """Draw the rendering options.

        :param context:
            Context.
        """

        # Get a reference to the layout of the panel
        layout = self.layout

        # Rendering options
        rendering_row = self.layout.row()
        rendering_row.label(text='Rendering Options:', icon='RENDER_STILL')

        # Rendering resolution
        rendering_resolution_row = self.layout.row()
        rendering_resolution_row.label(text='Resolution:')
        rendering_resolution_row.prop(context.scene, 'MorphologyRenderingResolution', expand=True)

        # Add the frame resolution option
        if context.scene.MeshRenderingResolution == \
                vmv.enums.Meshing.Rendering.Resolution.FIXED_RESOLUTION:

            # Frame resolution option (only for the close up mode)
            frame_resolution_row = self.layout.row()
            frame_resolution_row.label(text='Frame Resolution:')
            frame_resolution_row.prop(context.scene, 'MorphologyFrameResolution')
            vmv.interface.ui.ui_options.morphology.resolution_basis = context.scene.MorphologyFrameResolution

        # Otherwise, add the scalimport vmv.builderse factor option
        else:

            # Scale factor option
            scale_factor_row = self.layout.row()
            scale_factor_row.label(text='Resolution Scale:')
            scale_factor_row.prop(context.scene, 'MorphologyFrameScaleFactor')
            vmv.interface.ui.ui_options.morphology.resolution_scale_factor = context.scene.MorphologyFrameScaleFactor

        # Rendering view column
        view_row = self.layout.column()
        view_row.prop(context.scene, 'MorphologyRenderingViews', icon='AXIS_FRONT')
        view_row.operator('render_morphology.image', icon='MESH_DATA')

        vmv.ui_options.morphology.camera_view = context.scene.MorphologyRenderingViews

        # Render animation row
        render_animation_row = self.layout.row()
        render_animation_row.label(text='Render Animation:', icon='CAMERA_DATA')
        render_animations_buttons_row = self.layout.row(align=True)
        render_animations_buttons_row.operator('render_morphology.360', icon='FORCE_MAGNETIC')

        # Rendering progress bar
        rendering_progress_row = self.layout.row()
        rendering_progress_row.prop(context.scene, 'MorphologyRenderingProgress')
        rendering_progress_row.enabled = False

    ################################################################################################
    # @draw_morphology_export_options
    ################################################################################################
    def draw_morphology_export_options(self,
                                       context):
        """Draw the morphology export button.

        :param context:
            Context.
        """

        # Get a reference to the layout of the panel
        layout = self.layout

        # Saving meshes parameters
        save_mesh_row = self.layout.row()
        save_mesh_row.label(text='Export Morphology As:', icon='MESH_UVSPHERE')

        # Exported format column
        format_column = self.layout.column()
        format_column.prop(context.scene, 'ExportedMeshFormat', icon='GROUP_VERTEX')
        format_column.operator('export.morphology', icon='MESH_DATA')

    ################################################################################################
    # @draw
    ################################################################################################
    def draw(self, context):
        """Draw the panel.

        :param context:
            Panel context.
        """

        # Draw the morphology reconstruction options
        self.draw_morphology_reconstruction_options(context=context)

        # Draw the morphology color options
        self.draw_morphology_color_options(context=context)

        # Draw the morphology reconstruction button
        self.draw_morphology_reconstruction_button(context=context)

        # Draw the morphology rendering options
        self.draw_morphology_rendering_options(context=context)

        # Draw the morphology export options
        self.draw_morphology_export_options(context=context)

        # If the morphology is loaded, enable the layout, otherwise make it disabled by default
        if vmv.interface.ui_morphology_loaded:
            self.layout.enabled = True
        else:
            self.layout.enabled = False


####################################################################################################
# @VMVReconstructMorphology
####################################################################################################
class VMVReconstructMorphology(bpy.types.Operator):
    """Reconstructs the mesh of the vasculature"""

    # Operator parameters
    bl_idname = "reconstruct.morphology"
    bl_label = "Reconstruct Morphology"
    bl_options = {'REGISTER'}

    # Timer parameters
    event_timer = None
    #timer_limits = bpy.props.IntProperty(default=0)

    # The builder that will be used to build the morphology
    morphology_builder = None

    # The number of the components that needs to be built to say that the morphology is
    # reconstructed
    total_components = 0

    # The reconstructed components so far during the iteration
    i_component = 0

    ################################################################################################
    # @modal
    ################################################################################################
    def modal(self,
              context,
              event):
        """Threading and non-blocking handling.

        :param context:
            Panel context.
        :param event:
            A given event for the panel.
        """

        # Cancelling event, if using right click or exceeding the time limit of the simulation
        if event.type in {'RIGHTMOUSE', 'ESC'} or self.i_component > self.total_components - 1:

            # Reset the timer limits
            self.i_component = 0

            # Refresh the panel context
            self.cancel(context)

            # Done
            return {'FINISHED'}

        # Update the progress shell
        vmv.utilities.show_progress('Progress', self.i_component, self.total_components)

        # Reconstruct the component i (mainly the section)
        #self.morphology_builder.build_component(
        #    vmv.interface.ui.ui_morphology.sections_list[self.i_component])

        self.morphology_builder.build_component(self.i_component)

        # Next component
        self.i_component += 1

        # Update the progress bar
        progress = int(100.0 * self.i_component / float(self.total_components))
        context.scene.ReconstructionProgress = progress

        # View all the objects in the scene
        # vmv.scene.ops.view_all_scene()

        # Next frame
        return {'PASS_THROUGH'}

    ################################################################################################
    # @execute
    ################################################################################################
    def execute(self,
                context):
        """Executes the operator

        Keyword arguments:
        :param context:
            Operator context.
        :return:
            {'FINISHED'}
        """

        # Clear the scene
        vmv.scene.ops.clear_scene()

        # Make sure that the morphology isn loaded and valid in memory
        if not vmv.interface.ui_morphology_loaded:
            print('ERROR: Morphology is not loaded')

        # Construct the skeleton builder
        # Disconnected segments builder
        if vmv.interface.ui.ui_options.morphology.reconstruction_method == \
                vmv.enums.Skeletonization.Method.DISCONNECTED_SEGMENTS:
            self.morphology_builder = vmv.builders.DisconnectedSegmentsBuilder(
                morphology=vmv.interface.ui.ui_morphology, options=vmv.interface.ui.ui_options)

        # Disconnected sections builder
        elif vmv.interface.ui.ui_options.morphology.reconstruction_method == \
                vmv.enums.Skeletonization.Method.DISCONNECTED_SECTIONS:

            self.morphology_builder = vmv.builders.DisconnectedSectionsBuilder(
                morphology=vmv.interface.ui.ui_morphology,
                options=vmv.interface.ui.ui_options)
            self.total_components = len(vmv.interface.ui.ui_morphology.sections_list)

        # Connected sections builder
        elif vmv.interface.ui.ui_options.morphology.reconstruction_method == \
                vmv.enums.Skeletonization.Method.CONNECTED_SECTIONS:
            self.morphology_builder = vmv.builders.ConnectedSectionsBuilder(
                morphology=vmv.interface.ui.ui_morphology, options=vmv.interface.ui.ui_options)

        # Connected sections builder
        elif vmv.interface.ui.ui_options.morphology.reconstruction_method == \
                vmv.enums.Skeletonization.Method.CONNECTED_SKELETON:
            #self.morphology_builder = vmv.builders.CenterLineSkeletonBuilder(
            #    morphology=vmv.interface.ui.ui_morphology, options=vmv.interface.ui.ui_options)
            self.morphology_builder = vmv.builders.ConnectedSkeletonBuilder(
                morphology=vmv.interface.ui.ui_morphology, options=vmv.interface.ui.ui_options)
        else:
            return {'FINISHED'}

        # Progressive reconstruction
        if context.scene.ProgressiveReconstruction:

            # Returns the total number of components to be drawn for the RUNNING_MODAL option
            self.total_components = self.morphology_builder.get_number_components()

        # Direct reconstruction
        else:

            # Build the morphology skeleton directly
            # NOTE: each builder must have this function @build_skeleton() implemented in it
            self.morphology_builder.build_skeleton()

            # Done, return {'FINISHED'}
            return {'FINISHED'}

        # Use the event timer to update the UI
        wm = context.window_manager
        self.event_timer = wm.event_timer_add(time_step=0.1, window=context.window)
        wm.modal_handler_add(self)

        # Done
        return {'RUNNING_MODAL'}

    ################################################################################################
    # @cancel
    ################################################################################################
    def cancel(self, context):
        """Cancel the panel processing and return to the interaction mode.

        :param context:
            Panel context.
        """

        # Multi-threading
        wm = context.window_manager
        wm.event_timer_remove(self.event_timer)

        # Show the progress, Done
        vmv.utilities.show_progress('Progress', 100.0, 100.0, done=True)

        # Report the process termination in the UI
        self.report({'INFO'}, 'Building Morphology Done')


####################################################################################################
# @VMVRenderMorphologyImage
####################################################################################################
class VMVRenderMorphologyImage(bpy.types.Operator):
    """Renders an image of the morphology of the vasculature"""

    # Operator parameters
    bl_idname = "render_morphology.image"
    bl_label = "Render Image"

    ################################################################################################
    # @execute
    ################################################################################################
    def execute(self,
                context):
        """Executes the operator

        Keyword arguments:
        :param context:
            Operator context.
        :return:
            {'FINISHED'}
        """
        import vmv

        # Ensure that there is a valid directory where the images will be written to
        if vmv.interface.ui.ui_options.io.output_directory is None:
            self.report({'ERROR'}, vmv.consts.Messages.PATH_NOT_SET)
            return {'FINISHED'}

        if not vmv.file.ops.path_exists(context.scene.OutputDirectory):
            self.report({'ERROR'}, vmv.consts.Messages.INVALID_OUTPUT_PATH)
            return {'FINISHED'}

        # Create the images directory if it does not exist
        if not vmv.file.ops.path_exists(vmv.interface.ui_options.io.images_directory):
            vmv.file.ops.clean_and_create_directory(vmv.interface.ui_options.io.images_directory)

        # Report the process starting in the UI
        self.report({'INFO'}, 'Morphology Rendering ... Wait')

        import vmv.bbox

        # Compute the bounding box for the available meshes only
        rendering_bbox = vmv.bbox.compute_scene_bounding_box_for_curves()

        # Image name
        image_name = 'MORPHOLOGY_FRONT_MID_SHOT_%s' % vmv.interface.ui_options.morphology.label

        # Stretch the bounding box by few microns
        rendering_bbox.extend_bbox(delta=vmv.consts.Image.GAP_DELTA)

        # Render the morphology
        import vmv.rendering
        vmv.rendering.render(
            bounding_box=rendering_bbox,
            camera_view=vmv.ui_options.morphology.camera_view,
            image_resolution=context.scene.MorphologyFrameResolution,
            image_name=image_name,
            image_directory=vmv.interface.ui_options.io.images_directory,
            keep_camera_in_scene=context.scene.KeepSomaCameras)

        # Report the process termination in the UI
        self.report({'INFO'}, 'Rendering Morphology Done')

        return {'FINISHED'}


####################################################################################################
# @VMVRenderMesh360
####################################################################################################
class VMVRenderMorphology360(bpy.types.Operator):
    """Render a 360 view of the reconstructed mesh"""

    # Operator parameters
    bl_idname = "render_morphology.360"
    bl_label = "Render 360"

    # Timer parameters
    event_timer = None
    # timer_limits = bpy.props.IntProperty(default=0)

    # 360 bounding box
    bounding_box_360 = None

    # Output data
    output_directory = None

    ################################################################################################
    # @modal
    ################################################################################################
    def modal(self, context, event):
        """
        Threading and non-blocking handling.

        :param context: Panel context.
        :param event: A given event for the panel.
        """

        # Get a reference to the scene
        scene = context.scene
        """
        # Cancelling event, if using right click or exceeding the time limit of the simulation
        if event.type in {'RIGHTMOUSE', 'ESC'} or self.timer_limits > 360:
            # Reset the timer limits
            self.timer_limits = 0

            # Refresh the panel context
            self.cancel(context)

            # Done
            return {'FINISHED'}

        # Timer event, where the function is executed here on a per-frame basis
        if event.type == 'TIMER':

            # Set the frame name
            image_name = '%s/%s' % (
                self.output_directory, '{0:05d}'.format(self.timer_limits))

            # Render at a specific resolution
            if context.scene.MeshRenderingResolution == \
<<<<<<< HEAD
                    vmv.enums.Meshing.Rendering.Resolution.FIXED_RESOLUTION:

                # Render the image
                vmv.rendering.NeuronMeshRenderer.render_at_angle(
                    mesh_objects=vmv.interface.ui_reconstructed_mesh,
                    angle=self.timer_limits,
                    bounding_box=self.bounding_box_360,
                    camera_view=vmv.enums.Camera.View.FRONT_360,
=======
                    vmv.enums.Meshing.Rendering.Resolution.FIXED_RESOLUTION:

                # Render the image
                vmv.rendering.NeuronMeshRenderer.render_at_angle(
                    mesh_objects=vmv.interface.ui_reconstructed_mesh,
                    angle=self.timer_limits,
                    bounding_box=self.bounding_box_360,
                    camera_view=vmv.enums.Camera.View.FRONT_360,
>>>>>>> Adding sketched.
                    image_resolution=context.scene.MeshFrameResolution,
                    image_name=image_name)

            # Render at a specific scale factor
            else:

                # Render the image
<<<<<<< HEAD
                vmv.rendering.NeuronMeshRenderer.render_at_angle_to_scale(
                    mesh_objects=vmv.interface.ui_reconstructed_mesh,
                    angle=self.timer_limits,
                    bounding_box=self.bounding_box_360,
                    camera_view=vmv.enums.Camera.View.FRONT_360,
=======
                vmv.rendering.NeuronMeshRenderer.render_at_angle_to_scale(
                    mesh_objects=vmv.interface.ui_reconstructed_mesh,
                    angle=self.timer_limits,
                    bounding_box=self.bounding_box_360,
                    camera_view=vmv.enums.Camera.View.FRONT_360,
>>>>>>> Adding sketched.
                    image_scale_factor=context.scene.MeshFrameScaleFactor,
                    image_name=image_name)

            # Update the progress shell
<<<<<<< HEAD
            vmv.utilities.show_progress('Rendering', self.timer_limits, 360)
=======
            vmv.utilities.show_progress('Rendering', self.timer_limits, 360)
>>>>>>> Adding sketched.

            # Update the progress bar
            context.scene.NeuronMeshRenderingProgress = int(100 * self.timer_limits / 360.0)

            # Upgrade the timer limits
            self.timer_limits += 1
        """
        # Next frame
        return {'PASS_THROUGH'}

    ################################################################################################
    # @execute
    ################################################################################################
    def execute(self, context):
        """Execute the operator

        :param context:
            Panel context.
        """
        """
        # Ensure that there is a valid directory where the images will be written to
<<<<<<< HEAD
        if vmv.interface.ui_options.io.output_directory is None:
            self.report({'ERROR'}, vmv.consts.Messages.PATH_NOT_SET)
            return {'FINISHED'}

        if not vmv.file.ops.path_exists(context.scene.OutputDirectory):
            self.report({'ERROR'}, vmv.consts.Messages.INVALID_OUTPUT_PATH)
            return {'FINISHED'}

        # Create the sequences directory if it does not exist
        if not vmv.file.ops.path_exists(vmv.interface.ui_options.io.sequences_directory):
            vmv.file.ops.clean_and_create_directory(
                vmv.interface.ui_options.io.sequences_directory)
=======
        if vmv.interface.ui_options.io.output_directory is None:
            self.report({'ERROR'}, vmv.consts.Messages.PATH_NOT_SET)
            return {'FINISHED'}

        if not vmv.file.ops.path_exists(context.scene.OutputDirectory):
            self.report({'ERROR'}, vmv.consts.Messages.INVALID_OUTPUT_PATH)
            return {'FINISHED'}

        # Create the sequences directory if it does not exist
        if not vmv.file.ops.path_exists(vmv.interface.ui_options.io.sequences_directory):
            vmv.file.ops.clean_and_create_directory(
                vmv.interface.ui_options.io.sequences_directory)
>>>>>>> Adding sketched.

        # A reference to the bounding box that will be used for the rendering
        rendering_bbox = None

        # Compute the bounding box for a close up view
<<<<<<< HEAD
        if context.scene.MeshRenderingView == vmv.enums.Meshing.Rendering.View.CLOSE_UP_VIEW:

            # Compute the bounding box for a close up view
            rendering_bbox = vmv.bbox.compute_unified_extent_bounding_box(
                extent=context.scene.MeshCloseUpSize)

        # Compute the bounding box for a mid shot view
        elif context.scene.MeshRenderingView == vmv.enums.Meshing.Rendering.View.MID_SHOT_VIEW:

            # Compute the bounding box for the available meshes only
            rendering_bbox = vmv.bbox.compute_scene_bounding_box_for_meshes()
=======
        if context.scene.MeshRenderingView == vmv.enums.Meshing.Rendering.View.CLOSE_UP_VIEW:

            # Compute the bounding box for a close up view
            rendering_bbox = vmv.bbox.compute_unified_extent_bounding_box(
                extent=context.scene.MeshCloseUpSize)

        # Compute the bounding box for a mid shot view
        elif context.scene.MeshRenderingView == vmv.enums.Meshing.Rendering.View.MID_SHOT_VIEW:

            # Compute the bounding box for the available meshes only
            rendering_bbox = vmv.bbox.compute_scene_bounding_box_for_meshes()
>>>>>>> Adding sketched.

        # Compute the bounding box for the wide shot view that correspond to the whole morphology
        else:

            # Compute the full morphology bounding box
<<<<<<< HEAD
            rendering_bbox = vmv.skeleton.compute_full_morphology_bounding_box(
                morphology=vmv.interface.ui_morphology)

        # Compute a 360 bounding box to fit the arbors
        self.bounding_box_360 = vmv.bbox.compute_360_bounding_box(
            rendering_bbox, vmv.interface.ui_morphology.soma.centroid)

        # Stretch the bounding box by few microns
        self.bounding_box_360.extend_bbox(delta=vmv.consts.Image.GAP_DELTA)

        # Create a specific directory for this mesh
        self.output_directory = '%s/%s_mesh_360' % (
            vmv.interface.ui_options.io.sequences_directory,
            vmv.interface.ui_options.morphology.label)
        vmv.file.ops.clean_and_create_directory(self.output_directory)
=======
            rendering_bbox = vmv.skeleton.compute_full_morphology_bounding_box(
                morphology=vmv.interface.ui_morphology)

        # Compute a 360 bounding box to fit the arbors
        self.bounding_box_360 = vmv.bbox.compute_360_bounding_box(
            rendering_bbox, vmv.interface.ui_morphology.soma.centroid)

        # Stretch the bounding box by few microns
        self.bounding_box_360.extend_bbox(delta=vmv.consts.Image.GAP_DELTA)

        # Create a specific directory for this mesh
        self.output_directory = '%s/%s_mesh_360' % (
            vmv.interface.ui_options.io.sequences_directory,
            vmv.interface.ui_options.morphology.label)
        vmv.file.ops.clean_and_create_directory(self.output_directory)
>>>>>>> Adding sketched.

        # Use the event timer to update the UI during the soma building
        wm = context.window_manager
        self.event_timer = wm.event_timer_add(time_step=0.01, window=context.window)
        wm.modal_handler_add(self)
        """
        # Done
        return {'RUNNING_MODAL'}

    ################################################################################################
    # @cancel
    ################################################################################################
    def cancel(self, context):
        """
        Cancel the panel processing and return to the interaction mode.

        :param context: Panel context.
        """

        # Multi-threading
        wm = context.window_manager
        wm.event_timer_remove(self.event_timer)

        # Report the process termination in the UI
        self.report({'INFO'}, 'Morphology Rendering Done')

        # Confirm operation done
        return {'FINISHED'}


####################################################################################################
# @VMVReconstructMesh
####################################################################################################
class VMVExportMorphology(bpy.types.Operator):
    """Export the reconstructed mesh to a file"""

    # Operator parameters
    bl_idname = "export.morphology"
    bl_label = "Export"

    ################################################################################################
    # @execute
    ################################################################################################
    def execute(self,
                context):
        """Executes the operator

        Keyword arguments:
        :param context:
            Operator context.
        :return:
            {'FINISHED'}
        """


        """
        # Load the morphology file
<<<<<<< HEAD
        loading_result = vmv.interface.ui.load_morphology(self, context.scene)
=======
        loading_result = vmv.interface.ui.load_morphology(self, context.scene)
>>>>>>> Adding sketched.

        # If the result is None, report the issue
        if loading_result is None:
            self.report({'ERROR'}, 'Please select a morphology file')
            return {'FINISHED'}

        # Meshing technique
<<<<<<< HEAD
        meshing_technique = vmv.interface.ui_options.mesh.meshing_technique

        # Piece-wise watertight meshing
        if meshing_technique == vmv.enums.Meshing.Technique.PIECEWISE_WATERTIGHT:

            # Create the mesh builder
            mesh_builder = vmv.builders.PiecewiseBuilder(
                morphology=vmv.interface.ui_morphology, options=vmv.interface.ui_options)

            # Reconstruct the mesh
            vmv.interface.ui_reconstructed_mesh = mesh_builder.reconstruct_mesh()

        # Bridging
        elif meshing_technique == vmv.enums.Meshing.Technique.BRIDGING:

            # Create the mesh builder
            mesh_builder = vmv.builders.BridgingBuilder(
                morphology=vmv.interface.ui_morphology, options=vmv.interface.ui_options)

            # Reconstruct the mesh
            vmv.interface.ui_reconstructed_mesh = mesh_builder.reconstruct_mesh()

        # Union
        elif meshing_technique == vmv.enums.Meshing.Technique.UNION:

            # Create the mesh builder
            mesh_builder = vmv.builders.UnionBuilder(
                morphology=vmv.interface.ui_morphology, options=vmv.interface.ui_options)

            # Reconstruct the mesh
            vmv.interface.ui_reconstructed_mesh = mesh_builder.reconstruct_mesh()

        # Extrusion
        elif meshing_technique == vmv.enums.Meshing.Technique.EXTRUSION:

            # Create the mesh builder
            mesh_builder = vmv.builders.ExtrusionBuilder(
                morphology=vmv.interface.ui_morphology, options=vmv.interface.ui_options)

            # Reconstruct the mesh
            vmv.interface.ui_reconstructed_mesh = mesh_builder.reconstruct_mesh()

        elif meshing_technique == vmv.enums.Meshing.Technique.SKINNING:

            # Create the mesh builder
            mesh_builder = vmv.builders.SkinningBuilder(
                morphology=vmv.interface.ui_morphology, options=vmv.interface.ui_options)

            # Reconstruct the mesh
            vmv.interface.ui_reconstructed_mesh = mesh_builder.reconstruct_mesh()

        elif meshing_technique == vmv.enums.Meshing.Technique.META_OBJECTS:

            # Create the mesh builder
            mesh_builder = vmv.builders.MetaBuilder(
                morphology=vmv.interface.ui_morphology, options=vmv.interface.ui_options)

            # Reconstruct the mesh
            vmv.interface.ui_reconstructed_mesh = mesh_builder.reconstruct_mesh()
=======
        meshing_technique = vmv.interface.ui_options.mesh.meshing_technique

        # Piece-wise watertight meshing
        if meshing_technique == vmv.enums.Meshing.Technique.PIECEWISE_WATERTIGHT:

            # Create the mesh builder
            mesh_builder = vmv.builders.PiecewiseBuilder(
                morphology=vmv.interface.ui_morphology, options=vmv.interface.ui_options)

            # Reconstruct the mesh
            vmv.interface.ui_reconstructed_mesh = mesh_builder.reconstruct_mesh()

        # Bridging
        elif meshing_technique == vmv.enums.Meshing.Technique.BRIDGING:

            # Create the mesh builder
            mesh_builder = vmv.builders.BridgingBuilder(
                morphology=vmv.interface.ui_morphology, options=vmv.interface.ui_options)

            # Reconstruct the mesh
            vmv.interface.ui_reconstructed_mesh = mesh_builder.reconstruct_mesh()

        # Union
        elif meshing_technique == vmv.enums.Meshing.Technique.UNION:

            # Create the mesh builder
            mesh_builder = vmv.builders.UnionBuilder(
                morphology=vmv.interface.ui_morphology, options=vmv.interface.ui_options)

            # Reconstruct the mesh
            vmv.interface.ui_reconstructed_mesh = mesh_builder.reconstruct_mesh()

        # Extrusion
        elif meshing_technique == vmv.enums.Meshing.Technique.EXTRUSION:

            # Create the mesh builder
            mesh_builder = vmv.builders.ExtrusionBuilder(
                morphology=vmv.interface.ui_morphology, options=vmv.interface.ui_options)

            # Reconstruct the mesh
            vmv.interface.ui_reconstructed_mesh = mesh_builder.reconstruct_mesh()

        elif meshing_technique == vmv.enums.Meshing.Technique.SKINNING:

            # Create the mesh builder
            mesh_builder = vmv.builders.SkinningBuilder(
                morphology=vmv.interface.ui_morphology, options=vmv.interface.ui_options)

            # Reconstruct the mesh
            vmv.interface.ui_reconstructed_mesh = mesh_builder.reconstruct_mesh()

        elif meshing_technique == vmv.enums.Meshing.Technique.META_OBJECTS:

            # Create the mesh builder
            mesh_builder = vmv.builders.MetaBuilder(
                morphology=vmv.interface.ui_morphology, options=vmv.interface.ui_options)

            # Reconstruct the mesh
            vmv.interface.ui_reconstructed_mesh = mesh_builder.reconstruct_mesh()
>>>>>>> Adding sketched.

        else:

            # Invalid method
            self.report({'ERROR'}, 'Invalid Meshing Technique')
        """
        return {'FINISHED'}


####################################################################################################
# @register_panel
####################################################################################################
def register_panel():
    """Registers all the classes in this panel"""

    # Panel
    bpy.utils.register_class(VMVMorphologyPanel)

    # Mesh reconstruction button
    bpy.utils.register_class(VMVReconstructMorphology)

    # Mesh rendering buttons
    bpy.utils.register_class(VMVRenderMorphologyImage)
    bpy.utils.register_class(VMVRenderMorphology360)

    # Mesh export button
    bpy.utils.register_class(VMVExportMorphology)


####################################################################################################
# @unregister_panel
####################################################################################################
def unregister_panel():
    """Un-registers all the classes in this panel"""

    # Panel
    bpy.utils.unregister_class(VMVMorphologyPanel)

    # Mesh reconstruction button
    bpy.utils.unregister_class(VMVReconstructMorphology)

    # Mesh rendering buttons
    bpy.utils.unregister_class(VMVRenderMorphologyImage)
    bpy.utils.unregister_class(VMVRenderMorphology360)

    # Mesh export button
    bpy.utils.unregister_class(VMVExportMorphology)
