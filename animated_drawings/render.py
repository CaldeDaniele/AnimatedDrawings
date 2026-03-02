# Copyright (c) Meta Platforms, Inc. and affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import logging
import sys
import time


def start(user_mvc_cfg_fn: str):

    # build cfg
    t0 = time.perf_counter()
    from animated_drawings.config import Config
    cfg: Config = Config(user_mvc_cfg_fn)
    t_config = time.perf_counter() - t0

    # create view (OpenGL/glfw or Mesa context, shaders)
    t0 = time.perf_counter()
    from animated_drawings.view.view import View
    view = View.create_view(cfg.view)
    t_view = time.perf_counter() - t0

    # create scene (load BVH, build character meshes, retargeter)
    t0 = time.perf_counter()
    from animated_drawings.model.scene import Scene
    scene = Scene(cfg.scene)
    t_scene = time.perf_counter() - t0

    # create controller
    from animated_drawings.controller.controller import Controller
    controller = Controller.create_controller(cfg.controller, scene, view)

    # start the run loop
    controller.run()

    # Startup breakdown (so we see where time goes before the frame loop)
    if t_config or t_view or t_scene:
        print(
            f'[Animation startup] config: {t_config:.2f}s | view (GL init): {t_view:.2f}s | scene (BVH+mesh): {t_scene:.2f}s'
        )


if __name__ == '__main__':
    logging.basicConfig(filename='log.txt', level=logging.DEBUG)

    # user-specified mvc configuration filepath. Can be absolute, relative to cwd, or relative to ${AD_ROOT_DIR}
    user_mvc_cfg_fn = sys.argv[1]

    start(user_mvc_cfg_fn)
