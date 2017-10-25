from openmdao.api import Group
from openaerostruct.aerodynamics.assemble_aic import AssembleAIC
from openaerostruct.aerodynamics.circulations import Circulations
from openaerostruct.aerodynamics.forces import Forces

class VLMStates(Group):
    """ Group that contains the aerodynamic states. """

    def initialize(self):
        self.metadata.declare('surfaces', type_=list)

    def setup(self):
        surfaces = self.metadata['surfaces']

        tot_panels = 0
        for surface in surfaces:
            ny = surface['num_y']
            nx = surface['num_x']
            tot_panels += (nx - 1) * (ny - 1)

        self.add_subsystem('assembly',
             AssembleAIC(surfaces=surfaces),
             promotes_inputs=['*'],
             promotes_outputs=['AIC', 'rhs'])

        self.add_subsystem('circulations',
             Circulations(size=int(tot_panels)),
             promotes_inputs=['AIC', 'rhs'],
             promotes_outputs=['circulations'])

        self.add_subsystem('forces',
             Forces(surfaces=surfaces),
             promotes_inputs=['*'],
             promotes_outputs=['*'])