from openmdao.api import Group, ExplicitComponent
from openaerostruct.geometry.new_geometry_mesh import GeometryMesh
from openaerostruct.geometry.bsplines import Bsplines
from openaerostruct.structures.spatial_beam_states import SpatialBeamStates
from openaerostruct.structures.spatial_beam_functionals import SpatialBeamFunctionals
from openaerostruct.structures.spatial_beam_setup import SpatialBeamSetup
from openaerostruct.structures.materials_tube import MaterialsTube


class SpatialBeamAlone(Group):
    """ Group that contains everything needed for a structural-only problem. """

    def initialize(self):
        self.metadata.declare('surface', type_=dict, required=True)
        self.metadata.declare('indep_var_comp', type_=ExplicitComponent, required=True)

    def setup(self):
        surface = self.metadata['surface']
        indep_var_comp = self.metadata['indep_var_comp']
        ny = surface['mesh'].shape[1]
        num_thickness_cp = 3

        # Add structural components to the surface-specific group
        self.add_subsystem('indep_vars',
                 indep_var_comp,
                 promotes=['*'])
                 
        self.add_subsystem('mesh',
                 GeometryMesh(surface=surface),
                 promotes_outputs=['mesh', 'radius'])

        self.add_subsystem('thickness_bsp', Bsplines(
            in_name='thickness_cp', out_name='thickness',
            num_cp=num_thickness_cp, num_pt=int(ny-1)),
            promotes_inputs=['thickness_cp'], promotes_outputs=['thickness'])

        self.add_subsystem('tube',
            MaterialsTube(surface=surface),
            promotes_inputs=['thickness', 'radius'], promotes_outputs=['A', 'Iy', 'Iz', 'J'])

        self.add_subsystem('struct_setup',
            SpatialBeamSetup(surface=surface),
            promotes_inputs=['mesh', 'A', 'Iy', 'Iz', 'J'], promotes_outputs=['nodes', 'K'])

        self.add_subsystem('struct_states',
            SpatialBeamStates(surface=surface),
            promotes_inputs=['K', 'forces', 'loads'], promotes_outputs=['disp'])

        self.add_subsystem('struct_funcs',
            SpatialBeamFunctionals(surface=surface),
            promotes_inputs=['thickness', 'radius', 'A', 'nodes', 'disp'], promotes_outputs=['thickness_intersects', 'structural_weight', 'cg_location', 'vonmises', 'failure'])
