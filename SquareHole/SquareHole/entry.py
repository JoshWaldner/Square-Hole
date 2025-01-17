import math
import adsk.core
import os

import adsk.fusion
import adsk.cam
from ...lib import fusionAddInUtils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = 'Square Hole'
CMD_Description = 'Transform round holes to square'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the 
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidModifyPanel'
COMMAND_BESIDE_ID = 'FusionDeleteCommand'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []


# Executed when add-in is run.
def start():
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)

    # Specify if the command is promoted to the main toolbar. 
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    #futil.log(f'{CMD_NAME} Command Created Event')

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs

    # TODO Define the dialog for your command by adding different inputs to the command.

    # Create a simple text box input.
    BodySelect = inputs.addSelectionInput("BodySelecter", "Select Bodies", "Select Bodies")
    BodySelect.addSelectionFilter("SolidBodies")
    BodySelect.setSelectionLimits(0, 0)

    # TODO Connect to the events that are needed by this command.
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    #futil.log(f'{CMD_NAME} Command Execute Event')
    inputs = args.command.commandInputs
    app = adsk.core.Application.get()
    ui = app.userInterface
    des: adsk.fusion.Design = app.activeProduct
    root: adsk.fusion.Component = des.rootComponent
    tempBrepMgr = adsk.fusion.TemporaryBRepManager.get()
    # TODO ******************************** Your code here ********************************
    Bodies = []
    count = 1
    BodySelecter: adsk.core.SelectionCommandInput = inputs.itemById("BodySelecter")
    for Body in range(0, BodySelecter.selectionCount):
        SelectedBody: adsk.fusion.BRepBody = BodySelecter.selection(Body).entity
        Bodies.append(SelectedBody)
    if len(Bodies) > 0:
        progressDialog = ui.createProgressDialog()
        progressDialog.cancelButtonText = 'Cancel'
        progressDialog.isBackgroundTranslucent = False
        progressDialog.isCancelButtonShown = True
        
        # Show dialog
        progressDialog.show('Progress Dialog', "", 0, len(Bodies)) 
        for body in Bodies:
            progressDialog.message = f"{body.name}\n %v of %m\n %p% Completed"
            body: adsk.fusion.BRepBody
            if progressDialog.wasCancelled:
                break
            for Surface in body.faces:
                SurfaceCount = 1
                ProgressBar = ui.progressBar
                ProgressBar.show("Calculating", 1, body.faces.count)
                if Surface.geometry.objectType == 'adsk::core::Cylinder' and Surface.isParamReversed is True:
                    CylinderOrigin: adsk.core.Point3D = Surface.geometry.origin
                    CylinderAxis: adsk.core.Vector3D = Surface.geometry.axis
                    CrossAxis = root.constructionAxes.createInput()
                    CrossAxis.setByNormalToFaceAtPoint(Surface, CylinderOrigin)
                    PerpAxis = root.constructionAxes.add(CrossAxis)
                    Length = (Surface.area - 2 * math.pi * Surface.geometry.radius**2) / (2 * math.pi * Surface.geometry.radius)
                    orientedBoundingBox3D = adsk.core.OrientedBoundingBox3D.create(CylinderOrigin, CylinderAxis, PerpAxis.geometry.direction, 100000, Surface.geometry.radius*2, Surface.geometry.radius*2)
                    Box = tempBrepMgr.createBox(orientedBoundingBox3D)
                    TMPbody = root.bRepBodies.add(Box)
                    TmpCollection = adsk.core.ObjectCollection.create()
                    TmpCollection.add(TMPbody)
                    Combines = root.features.combineFeatures
                    CombineInput: adsk.fusion.CombineFeatureInput  = Combines.createInput(body, TmpCollection)
                    CombineInput.isKeepToolBodies = False
                    CombineInput.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
                    Combine = Combines.add(CombineInput)
                    PerpAxis.deleteMe()
                    ProgressBar.progressValue = SurfaceCount
                    SurfaceCount += 1
                    adsk.doEvents()
            progressDialog.progressValue = count        
            count += 1
            

        progressDialog.hide()       

            
        



# This event handler is called when the command needs to compute a new preview in the graphics window.
def command_preview(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    #futil.log(f'{CMD_NAME} Command Preview Event')
    inputs = args.command.commandInputs


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs

    # General logging for debug.
    #futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # General logging for debug.
    #futil.log(f'{CMD_NAME} Validate Input Event')
    pass
    # inputs = args.inputs
    
    # # Verify the validity of the input values. This controls if the OK button is enabled or not.
    # valueInput = inputs.itemById('value_input')
    # if valueInput.value >= 0:
    #     args.areInputsValid = True
    # else:
    #     args.areInputsValid = False
        

# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    #futil.log(f'{CMD_NAME} Command Destroy Event')

    global local_handlers
    local_handlers = []


            
