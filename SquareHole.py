# Assuming you have not changed the general structure of the template no modification is needed in this file.
from . import SquareHole
from .lib import fusionAddInUtils as futil


def run(context):
    try:
        # This will run the start function in each of your commands as defined in commands/__init__.py
        SquareHole.start()

    except:
        futil.handle_error('run')


def stop(context):
    try:
        # Remove all of the event handlers your app has created
        futil.clear_handlers()

        # This will run the start function in each of your commands as defined in commands/__init__.py
        SquareHole.stop()

    except:
        futil.handle_error('stop')