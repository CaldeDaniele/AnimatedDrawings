# Animated Drawings

![Sequence 02](https://user-images.githubusercontent.com/6675724/219223438-2c93f9cb-d4b5-45e9-a433-149ed76affa6.gif)

**_Update 09-03-25: This project has been a joy to share with you all. Thanks to this community for your creativity and support along the way. I'm moving on to new adventures and won't be able to maintain this repository anymore, so I've chosen to archive it. If you have questions or want to say hello in the future, come find me at [www.hjessmith.com](http://www.hjessmith.com)._**
 
This repo contains an implementation of the algorithm described in the paper, [A Method for Animating Children's Drawings of the Human Figure](https://dl.acm.org/doi/10.1145/3592788). In addition, this repo aims to be a useful creative tool in its own right, allowing you to flexibly create animations starring your own drawn characters. Here's a [video overview](https://www.youtube.com/watch?v=WsMUKQLVsOI) of the project. If you do create something fun with this, let us know! Use hashtag **#FAIRAnimatedDrawings**, or tag me on twitter: [@hjessmith](https://twitter.com/hjessmith/).




## Installation
*This project has been tested with macOS Ventura 13.2.1 and Ubuntu 18.04. If you're installing on another operating system, you may encounter issues.*

We *strongly* recommend activating a Python virtual environment prior to installing Animated Drawings.
Conda's Miniconda is a great choice. Follow [these steps](https://conda.io/projects/conda/en/stable/user-guide/install/index.html) to download and install it. Then run the following commands:

````bash
    # create and activate the virtual environment
    conda create --name animated_drawings python=3.8.13
    conda activate animated_drawings

    # clone AnimatedDrawings and use pip to install
    git clone https://github.com/facebookresearch/AnimatedDrawings.git
    cd AnimatedDrawings
    pip install -e .
````

Mac M1/M2 users: if you get architecture errors, make sure your `~/.condarc` does not have `osx-64`, but only `osx-arm64` and `noarch` in its subdirs listing. You can see that it's going to go sideways as early as `conda create` because it will show `osx-64` instead of `osx-arm64` versions of libraries under "The following NEW packages will be INSTALLED".

## Using Animated Drawings

You can animate drawings in two main ways: **interactively** (Python + config files, see Quick Start below) or via the **HTTP API** (Docker: send an image and motion config, get back a GIF). The API is described in [Animating Your Own Drawing → Option 1: Docker with HTTP API](#option-1-docker-with-http-api-recommended).

### Quick Start
Now that everything's set up, let's animate some drawings! To get started, follow these steps:
1. Open a terminal and activate the animated_drawings conda environment:
````bash
~ % conda activate animated_drawings
````

2. Ensure you're in the root directory of AnimatedDrawings:
````bash
(animated_drawings) ~ % cd {location of AnimatedDrawings on your computer}
````

3. Start up a Python interpreter:
````bash
(animated_drawings) AnimatedDrawings % python
````

4. Copy and paste the follow two lines into the interpreter:
````python
from animated_drawings import render
render.start('./examples/config/mvc/interactive_window_example.yaml')
````

If everything is installed correctly, an interactive window should appear on your screen.
(Use spacebar to pause/unpause the scene, arrow keys to move back and forth in time, and q to close the screen.)

<img src='./media/interactive_window_example.gif' width="256" height="256" /> </br></br></br>

There's a lot happening behind the scenes here. Characters, motions, scenes, and more are all controlled by configuration files, such as `interactive_window_example.yaml`. Below, we show how different effects can be achieved by varying the config files. You can learn more about the [config files here](examples/config/README.md).

### Export MP4 video

Suppose you'd like to save the animation as a video file instead of viewing it directly in a window. Specify a different example config by copying these lines into the Python interpreter:

````python
from animated_drawings import render
render.start('./examples/config/mvc/export_mp4_example.yaml')
````

Instead of an interactive window, the animation was saved to a file, video.mp4, located in the same directory as your script.

<img src='./media/mp4_export_video.gif' width="256" height="256" /> </br></br></br>

### Export transparent .gif

Perhaps you'd like a transparent .gif instead of an .mp4? Copy these lines in the Python interpreter instead:

````python
from animated_drawings import render
render.start('./examples/config/mvc/export_gif_example.yaml')
````

Instead of an interactive window, the animation was saved to a file, video.gif, located in the same directory as your script.

<img src='./media/gif_export_video.gif' width="256" height="256" /> </br></br></br>

### Headless Rendering

If you'd like to generate a video headlessly (e.g. on a remote server accessed via ssh), you'll need to specify `USE_MESA: True` within the `view` section of the config file.

````yaml
    view:
      USE_MESA: True
````

### Animating Your Own Drawing

All of the examples above use drawings with pre-existing annotations.
To understand what we mean by *annotations* here, look at one of the 'pre-rigged' character's [annotation files](examples/characters/char1/).
You can use whatever process you'd like to create those annotations files and, as long as they are valid, AnimatedDrawings will give you an animation.

So you'd like to animate your own drawn character.
I wouldn't want you to create those annotation files manually. That would be tedious.
To make it fast and easy, we've trained a drawn humanoid figure detector and pose estimator and provided scripts to automatically generate annotation files from the model predictions.
There are currently two options for setting this up.

#### Option 1: Docker with HTTP API (recommended)

A single Docker image runs **TorchServe** (detection/pose) and a **REST API** that accepts an image and a motion config and returns an animated GIF. You can use it from any client (browser, `curl`, another app) without running Python locally.

**1. Install and start Docker**

- [Install Docker Desktop](https://docs.docker.com/get-docker/) and ensure it is running.
- From the **AnimatedDrawings root directory**, run:

  **Mac / Linux:**

  ````bash
  ./start_torchserve.sh
  ````

  **Windows (PowerShell):**

  ````powershell
  .\start_torchserve.ps1
  ````

  The first run builds two images (base TorchServe, then API) and can take several minutes. If you see "cannot allocate memory", give Docker more RAM (e.g. 16GB in Docker Desktop → Settings → Resources).

**2. Use the API**

Once the script reports "API OK", you have:

| What | URL |
|------|-----|
| **Swagger UI** (try the API in the browser) | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **OpenAPI schema** | [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) |
| **Health check** | `GET http://localhost:8000/health` |
| **Generate GIF** | `POST http://localhost:8000/gif` |

**Generate a GIF** — send an image and a motion config (multipart form):

- `image`: PNG or JPG file.
- `motion_cfg`: motion name (e.g. `dab`, `wave_hello`, `zombie`, `jumping_jacks`) or path like `config/motion/dab.yaml`.
- `retarget_cfg`: (optional) e.g. `fair1_ppf` (default).

Example with `curl`:

````bash
curl -X POST "http://localhost:8000/gif" \
  -F "image=@path/to/your/drawing.png" \
  -F "motion_cfg=dab" \
  -o animation.gif
````

The response body is the GIF file. You can also call the API from another project (e.g. a web app or backend) by posting to `http://localhost:8000/gif` (or your server’s host/port).

**Files involved**

- `api_server.py` — FastAPI app (POST /gif, GET /health).
- `gif_pipeline.py` — pipeline: image → annotations → render → video.gif.
- `torchserve/Dockerfile.api` — Dockerfile for the all-in-one image.
- `start_torchserve.sh` / `start_torchserve.ps1` — build and run the container (TorchServe + API on ports 8080/8081 and 8000).

#### Option 1b: Docker (TorchServe only, no API)

If you only need TorchServe and prefer to run the pipeline from the command line (e.g. `image_to_animation.py`), you can build and run the base image by hand:

1. [Install Docker Desktop](https://docs.docker.com/get-docker/) and ensure it is running.
2. From the Animated Drawings root directory:

````bash
    cd torchserve
    docker build -t docker_torchserve .
    docker run -d --name docker_torchserve -p 8080:8080 -p 8081:8081 docker_torchserve
````

Wait ~10 seconds, then check: `curl http://localhost:8080/ping` should return `{"status":"Healthy"}`. If you get an empty reply, wait longer or increase Docker memory to 16GB.

Then, from the repo root (with conda env active), run the pipeline locally:

````bash
    cd examples
    python image_to_animation.py drawings/garlic.png garlic_out
````

The result is saved as `./garlic_out/video.gif`. You can pass a motion config as the third argument, e.g. `python image_to_animation.py drawings/garlic.png garlic_out config/motion/dab.yaml`.

<img src='./examples/drawings/garlic.png' height="256" /><img src='./media/garlic.gif' width="256" height="256" /></br></br></br>

#### Option 2: Running locally on macOS

Getting Docker working can be complicated, and it's unnecessary if you just want to play around with this locally.
Contributer @Gravityrail kindly submitted a script that sets up Torchserve locally on MacOS, no Docker required.

```bash
cd torchserve
./setup_macos.sh
torchserve --start --ts-config config.local.properties --foreground
```

With torchserve running locally like this, you can use the same command as before to make the garlic dance:

```bash 
python image_to_animation.py drawings/garlic.png garlic_out
```
### Fixing bad predictions
You may notice that, when you ran `python image_to_animation.py drawings/garlic.png garlic_out`, there were additional non-video files within `garlic_out`.
`mask.png`, `texture.png`, and `char_cfg.yaml` contain annotation results of the image character analysis step. These annotations were created from our model predictions.
If the mask predictions are incorrect, you can edit the mask with an image editing program like Paint or Photoshop.
If the joint predictions are incorrect, you can run `python fix_annotations.py` to launch a web interface to visualize, correct, and update the annotations. Pass it the location of the folder containing incorrect joint predictions (here we use `garlic_out/` as an example):

````bash
    (animated_drawings) examples % python fix_annotations.py garlic_out/
    ...
     * Running on http://127.0.0.1:5050
    Press CTRL+C to quit
````

Navigate to `http://127.0.0.1:5050` in your browser to access the web interface. Drag the joints into the appropriate positions, and hit `Submit` to save your edits.

Once you've modified the annotations, you can render an animation using them like so:

````bash
    # specify the folder where the fixed annoations are located
    (animated_drawings) examples % python annotations_to_animation.py garlic_out
````

### Adding multiple characters to scene
Multiple characters can be added to a video by specifying multiple entries within the config scene's 'ANIMATED_CHARACTERS' list.
To see for yourself, run the following commands from a Python interpreter within the AnimatedDrawings root directory:

````python
from animated_drawings import render
render.start('./examples/config/mvc/multiple_characters_example.yaml')
````
<img src='./examples/characters/char1/texture.png' height="256" /> <img src='./examples/characters/char2/texture.png' height="256" /> <img src='./media/multiple_characters_example.gif' height="256" />

### Adding a background image
Suppose you'd like to add a background to the animation. You can do so by specifying the image path within the config.
Run the following commands from a Python interpreter within the AnimatedDrawings root directory:

````python
from animated_drawings import render
render.start('./examples/config/mvc/background_example.yaml')
````

<img src='./examples/characters/char4/texture.png' height="256" /> <img src='./examples/characters/char4/background.png' height="256" /> <img src='./media/background_example.gif' height="256" />

### Using BVH Files with Different Skeletons
You can use any motion clip you'd like, as long as it is in BVH format.

If the BVH's skeleton differs from the examples used in this project, you'll need to create a new motion config file and retarget config file.
Once you've done that, you should be good to go.
The following code and resulting clip uses a BVH with completely different skeleton.
Run the following commands from a Python interpreter within the AnimatedDrawings root directory:

````python
from animated_drawings import render
render.start('./examples/config/mvc/different_bvh_skeleton_example.yaml')
````

<img src='./media/different_bvh_skeleton_example.gif' height="256" />

### Creating Your Own BVH Files
You may be wondering how you can create BVH files of your own.
You used to need a motion capture studio.
But now, thankfully, there are simple and accessible options for getting 3D motion data from a single RGB video.
For example, I created this Readme's banner animation by:
1. Recording myself doing a silly dance with my phone's camera.
2. Using [Rokoko](https://www.rokoko.com/) to export a BVH from my video.
3. Creating a new [motion config file](examples/config/README.md#motion) and [retarget config file](examples/config/README.md#retarget) to fit the skeleton exported by Rokoko.
4. Using AnimatedDrawings to animate the characters and export a transparent animated gif.
5. Combining the animated gif, original video, and original drawings in Adobe Premiere.
<img src='https://user-images.githubusercontent.com/6675724/219223438-2c93f9cb-d4b5-45e9-a433-149ed76affa6.gif' height="256" />

Here is an example of the configs I used apply my motion to a character. To use these config files, ensure that the Rokoko exports the BVH with the Mixamo skeleton preset:

 ````python
from animated_drawings import render
render.start('./examples/config/mvc/rokoko_motion_example.yaml')
 ````

It will show this in a new window:

![Sequence 01](https://user-images.githubusercontent.com/6675724/233157474-1506d219-c085-49f9-a537-43d6c1bae93a.gif)




### Adding Addition Character Skeletons
All of the example animations above depict "human-like" characters; they have two arms and two legs.
Our method is primarily designed with these human-like characters in mind, and the provided pose estimation model assumes a human-like skeleton is present.
But you can manually specify a different skeletons within the `character config` and modify the specified `retarget config` to support it.
If you're interested, look at the configuration files specified in the two examples below.


````python
from animated_drawings import render
render.start('./examples/config/mvc/six_arms_example.yaml')
````

<img src='https://user-images.githubusercontent.com/6675724/223584962-925ee5aa-11de-47e5-ace2-a6d5940b34ae.png' height="256" /><img src='https://user-images.githubusercontent.com/6675724/223585000-dc8acf4e-974d-4cae-998b-94543f5f42c8.gif' width="256" height="256" /></br></br></br>

````python
from animated_drawings import render
render.start('./examples/config/mvc/four_legs_example.yaml')
````

<img src='https://user-images.githubusercontent.com/6675724/223585033-f11e4e66-0443-405a-80e5-09b6aa0e335d.png' height="256" /><img src='https://user-images.githubusercontent.com/6675724/223585043-7ce9eac0-bb4c-4547-b038-c63ca2852ef2.gif' width="256" height="256" /></br></br></br>

If you're interested in animating quadrupeds specifically, you may want to check out [the quadruped example directory](examples/quadruped).

### Creating Your Own Config Files
If you want to create your own config files, see the [configuration file documentation](examples/config/README.md).

## Browser-Based Demo

If you'd like to animate a drawing of your own, but don't want to deal with downloading code and using the command line, check out our browser-based demo:

[www.sketch.metademolab.com](https://sketch.metademolab.com/)

## Paper & Citation
 If you find the resources in this repo helpful, please consider citing the accompanying paper, [A Method for Animating Children's Drawings of The Human Figure](https://dl.acm.org/doi/10.1145/3592788)).

Citation:

```
@article{10.1145/3592788,
author = {Smith, Harrison Jesse and Zheng, Qingyuan and Li, Yifei and Jain, Somya and Hodgins, Jessica K.},
title = {A Method for Animating Children’s Drawings of the Human Figure},
year = {2023},
issue_date = {June 2023},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
volume = {42},
number = {3},
issn = {0730-0301},
url = {https://doi.org/10.1145/3592788},
doi = {10.1145/3592788},
abstract = {Children’s drawings have a wonderful inventiveness, creativity, and variety to them. We present a system that automatically animates children’s drawings of the human figure, is robust to the variance inherent in these depictions, and is simple and straightforward enough for anyone to use. We demonstrate the value and broad appeal of our approach by building and releasing the Animated Drawings Demo, a freely available public website that has been used by millions of people around the world. We present a set of experiments exploring the amount of training data needed for fine-tuning, as well as a perceptual study demonstrating the appeal of a novel twisted perspective retargeting technique. Finally, we introduce the Amateur Drawings Dataset, a first-of-its-kind annotated dataset, collected via the public demo, containing over 178,000 amateur drawings and corresponding user-accepted character bounding boxes, segmentation masks, and joint location annotations.},
journal = {ACM Trans. Graph.},
month = {jun},
articleno = {32},
numpages = {15},
keywords = {2D animation, motion retargeting, motion stylization, Skeletal animation}
}
```

## Amateur Drawings Dataset

To obtain the Amateur Drawings Dataset, run the following two commands from the command line:

````bash
# download annotations (~275Mb)
wget https://dl.fbaipublicfiles.com/amateur_drawings/amateur_drawings_annotations.json

# download images (~50Gb)
wget https://dl.fbaipublicfiles.com/amateur_drawings/amateur_drawings.tar
````

If you'd like higher res images, they can be found on the releases (ad_orig_img_fs). They've been split into multiple chunks using the split cli. They are released under the same license as the original dataset. 

If you have feedback about the dataset, please fill out [this form](https://forms.gle/kE66yskh9uhtLbFz9).

## ChildlikeSHAPES

If you want this data set, construct the full archive from the chunks in the release page
````cat datachunk_* > full_archive.7z  #(pw=An1m8dR3610Ns)````


## Trained Model Weights

Trained model weights for human-like figure detection and pose estimation are included in the [repo releases](https://github.com/facebookresearch/AnimatedDrawings/releases). Model weights are released under [MIT license](https://github.com/facebookresearch/AnimatedDrawings/blob/main/LICENSE). The .mar files were generated using the OpenMMLab framework ([OpenMMDet Apache 2.0 License](https://github.com/open-mmlab/mmdetection/blob/main/LICENSE), [OpenMMPose Apache 2.0 License](https://github.com/open-mmlab/mmpose/blob/main/LICENSE))

## As-Rigid-As-Possible Shape Manipulation

These characters are deformed using [As-Rigid-As-Possible (ARAP) shape manipulation](https://www-ui.is.s.u-tokyo.ac.jp/~takeo/papers/takeo_jgt09_arapFlattening.pdf).
We have a Python implementation of the algorithm, located [here](https://github.com/fairinternal/AnimatedDrawings/blob/main/animated_drawings/model/arap.py), that might be of use to other developers.

## License
Animated Drawings code, model weights, and Amateur Drawings dataset is released under the [MIT license](https://github.com/fairinternal/AnimatedDrawings/blob/main/LICENSE). ChildlikeSHAPES dataset is released under [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) license. 
