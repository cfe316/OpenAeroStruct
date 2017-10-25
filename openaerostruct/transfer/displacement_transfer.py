from __future__ import division, print_function
import numpy as np

from openmdao.api import ExplicitComponent

try:
    from openaerostruct.fortran import OAS_API
    fortran_flag = True
    data_type = float
except:
    fortran_flag = False
    data_type = complex


class DisplacementTransfer(ExplicitComponent):
    """
    Perform displacement transfer.

    Apply the computed displacements on the original mesh to obtain
    the deformed mesh.

    Parameters
    ----------
    mesh[nx, ny, 3] : numpy array
        Flattened array defining the lifting surfaces.
    disp[ny, 6] : numpy array
        Flattened array containing displacements on the FEM component.
        Contains displacements for all six degrees of freedom, including
        displacements in the x, y, and z directions, and rotations about the
        x, y, and z axes.

    Returns
    -------
    def_mesh[nx, ny, 3] : numpy array
        Flattened array defining the lifting surfaces after deformation.
    """

    def initialize(self):
        self.metadata.declare('surface', type_=dict)

    def setup(self):
        self.surface = surface = self.metadata['surface']

        self.ny = surface['num_y']
        self.nx = surface['num_x']
        self.fem_origin = surface['fem_origin']

        self.add_input('mesh', val=np.random.rand(self.nx, self.ny, 3), units='m')
        self.add_input('disp', val=np.random.rand(self.ny, 6), units='m')
        self.add_output('def_mesh', val=np.random.rand(self.nx, self.ny, 3), units='m')

        if not fortran_flag:
            self.approx_partials('*', '*')

    def compute(self, inputs, outputs):
        mesh = inputs['mesh']
        disp = inputs['disp']

        # Get the location of the spar within the wing and save as w
        w = self.surface['fem_origin']

        # Run Fortran if possible
        if fortran_flag:
            def_mesh = OAS_API.oas_api.transferdisplacements(mesh, disp, w)

        else:

            # Get the location of the spar
            ref_curve = (1-w) * mesh[0, :, :] + w * mesh[-1, :, :]

            # Compute the distance from each mesh point to the nodal spar points
            Smesh = np.zeros(mesh.shape, dtype=data_type)
            for ind in range(self.nx):
                Smesh[ind, :, :] = mesh[ind, :, :] - ref_curve

            # Set up the mesh displacements array
            mesh_disp = np.zeros(mesh.shape, dtype=data_type)
            cos, sin = np.cos, np.sin

            # Loop through each spanwise FEM element
            for ind in range(self.ny):
                dx, dy, dz, rx, ry, rz = disp[ind, :]

                # 1 eye from the axis rotation matrices
                # -3 eye from subtracting Smesh three times
                T = -2 * np.eye(3, dtype=data_type)
                T[ 1:,  1:] += [[cos(rx), -sin(rx)], [ sin(rx), cos(rx)]]
                T[::2, ::2] += [[cos(ry),  sin(ry)], [-sin(ry), cos(ry)]]
                T[ :2,  :2] += [[cos(rz), -sin(rz)], [ sin(rz), cos(rz)]]

                # Obtain the displacements on the mesh based on the spar response
                mesh_disp[:, ind, :] += Smesh[:, ind, :].dot(T)
                mesh_disp[:, ind, 0] += dx
                mesh_disp[:, ind, 1] += dy
                mesh_disp[:, ind, 2] += dz

            # Apply the displacements to the mesh
            def_mesh = mesh + mesh_disp

        outputs['def_mesh'] = def_mesh

    if fortran_flag:
        def compute_partials(self, inputs, partials):

            d_mesh = np.zeros((self.nx, self.ny, 3))

            for j, val in enumerate(np.array(d_mesh).flatten()):
                d_out_b = np.array(d_mesh).flatten()
                d_out_b[:] = 0.
                d_out_b[j] = 1.
                d_mesh = d_out_b.reshape(d_mesh.shape)

                mesh = inputs['mesh']
                disp = inputs['disp']

                w = self.surface['fem_origin']

                d_mesh, d_disp = OAS_API.oas_api.transferdisplacements_b(mesh, disp, w, d_mesh, d_mesh)

                partials['def_mesh', 'mesh'][j, :] = d_mesh.flatten()
                partials['def_mesh', 'disp'][j, :] = d_disp.flatten()
