import adsk.core, adsk.fusion, traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('No active design open.', 'Error')
            return

        rootComp = design.rootComponent

        # Create or get live User Parameters
        userParams = design.userParameters
        
        def get_or_create_param(name, default_value, units, comment):
            param = userParams.itemByName(name)
            if not param:
                valInput = adsk.core.ValueInput.createByReal(default_value)
                param = userParams.add(name, valInput, units, comment)
            return param

        N_param = get_or_create_param('Stair_N', 5, '', 'Number of steps')
        l_param = get_or_create_param('Stair_l', 10, design.unitsManager.defaultLengthUnits, 'Tread depth')
        h_param = get_or_create_param('Stair_h', 7, design.unitsManager.defaultLengthUnits, 'Riser height')
        w_param = get_or_create_param('Stair_w', 36, design.unitsManager.defaultLengthUnits, 'Stair width')

        N = int(N_param.value)
        l_val = l_param.value
        h_val = h_param.value
        w_val = w_param.value

        # Create component
        newOcc = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = newOcc.component
        comp.name = 'Parametric_Staircase_Live'

        block_count = 0
        for ix in range(N):
            for iz in range(ix + 1):
                x = ix * l_val
                z = iz * h_val

                sketch = comp.sketches.add(comp.xYConstructionPlane)
                lines = sketch.sketchCurves.sketchLines
                p1 = adsk.core.Point3D.create(0, 0, 0)
                p2 = adsk.core.Point3D.create(l_val, w_val, 0)
                lines.addTwoPointRectangle(p1, p2)

                profile = sketch.profiles.item(0)

                extrudes = comp.features.extrudeFeatures
                extInput = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                extInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(h_val))
                extFeature = extrudes.add(extInput)
                body = extFeature.bodies.item(0)
                body.name = f'StairBlock_{ix}_{iz}'

                if x != 0 or z != 0:
                    moveFeats = comp.features.moveFeatures
                    transform = adsk.core.Matrix3D.create()
                    transform.translation = adsk.core.Vector3D.create(x, 0.0, z)
                    bodiesColl = adsk.core.ObjectCollection.create()
                    bodiesColl.add(body)
                    moveInput = moveFeats.createInput(bodiesColl, transform)
                    moveFeats.add(moveInput)

                block_count += 1

        # Hide sketches
        for sk in comp.sketches:
            sk.isLightBulbOn = False

        # === AUTO-MERGE INTO ONE SOLID (fixed version) ===
        if comp.bRepBodies.count > 1:
            combineFeats = comp.features.combineFeatures
            targetBody = comp.bRepBodies.item(0)
            toolBodies = adsk.core.ObjectCollection.create()
            for i in range(1, comp.bRepBodies.count):
                toolBodies.add(comp.bRepBodies.item(i))
            
            combineInput = combineFeats.createInput(targetBody, toolBodies)
            combineInput.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
            combineInput.isKeepToolBodies = False
            combineFeats.add(combineInput)
            targetBody.name = 'Staircase_Solid'

        ui.messageBox(
            f'Live Parametric Staircase Created Successfully!\n\n'
            f'Parameters (editable):\n'
            f'• Stair_N  = {N}\n'
            f'• Stair_l  = {l_val}\n'
            f'• Stair_h  = {h_val}\n'
            f'• Stair_w  = {w_val}\n\n'
            f'How to edit live:\n'
            f'1. Go to Modify → Change Parameters (or press Ctrl + Alt + P)\n'
            f'2. Modify any Stair_* value\n'
            f'3. Click OK — the staircase will rebuild automatically\n'
            f'   (including re-merging into one solid)\n\n'
            f'Press F to Zoom to Fit after changes.',
            'Success - Live Staircase Ready'
        )

    except Exception as e:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()), 'Script Error')