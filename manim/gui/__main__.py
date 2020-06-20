from manim import extract_scene
from manim import config
from manim.gui.config import gooey_cli
from manim import constants
from gooey import Gooey

@Gooey(program_name="Manim Community Gui",
        program_description="A GUI for Manim",
        advanced=True,
            menu=[{
        'name': 'File',
        'items': [{
                'type': 'AboutDialog',
                'menuTitle': 'About',
                'name': 'Manim Community GUI Renderer',
                'description': 'The UI renderer for Manim',
                'website': 'https://github.com/manimcommunity/manim',
                'developer': 'https://www.3blue1brown.com/',
                'license': 'MIT'
            }, {
                'type': 'Link',
                'menuTitle': 'Report an Error',
                'url': 'https://github.com/manimcommunity/manim/issues'
            }]
        },{
        'name': 'Help',
        'items': [{
            'type': 'Link',
            'menuTitle': 'Documentation',
            'url': 'https://manim.readthedocs.io/'
        }]
    }])
def main():
    args = gooey_cli()
    cfg = config.get_configuration(args)
    config.initialize_directories(cfg)
    config.initialize_tex(cfg)
    extract_scene.main(cfg)


if __name__ == "__main__":
    main()
