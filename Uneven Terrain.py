import adsk.core, adsk.fusion, traceback, math

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('No active design. Please open or create a design first.')
            return
        root = design.rootComponent
        unitsMgr = design.unitsManager

        # === USER INPUTS (l, w, h define the 3D cube) ===
        l_input = ui.inputBox('Enter length l (e.g. 1000 mm)', 'Terrain Size', '1000 mm')[0]
        w_input = ui.inputBox('Enter width w (e.g. 600 mm)', 'Terrain Size', '600 mm')[0]
        h_input = ui.inputBox('Enter max height h (e.g. 150 mm)', 'Terrain Size', '150 mm')[0]

        l = unitsMgr.evaluateExpression(l_input, 'cm')
        w = unitsMgr.evaluateExpression(w_input, 'cm')
        h = unitsMgr.evaluateExpression(h_input, 'cm')

        # === CUSTOMIZABLE PARAMETERS (edit here for different terrains) ===
        num_y_sections = 25      # more = smoother loft (25 is fast & stable)
        num_x_points = 40        # points per cross-section
        freq_x = 2.0             # main smooth waves along length
        freq_y = 1.5             # main smooth waves along width
        roughness = 0.4          # 0 = smooth; 0.3–0.6 = "not-so-smooth" uneven feel
        base_thickness = 2.0     # cm (20 mm) minimum solid thickness for printing & robot steps

        # === CREATE SOLID TERRAIN ===
        curves = []  # will hold closed profiles
        planes_list = []
        sketches_list = []

        for i in range(num_y_sections):
            y = i * w / (num_y_sections - 1)

            # Offset plane (parallel to XZ)
            planeInput = root.constructionPlanes.createInput()
            planeInput.setByOffset(root.xZConstructionPlane, adsk.core.ValueInput.createByReal(y))
            plane = root.constructionPlanes.add(planeInput)
            planes_list.append(plane)

            # Sketch on plane
            sk = root.sketches.add(plane)
            sketches_list.append(sk)
            points = adsk.core.ObjectCollection.create()

            for j in range(num_x_points):
                x = j * l / (num_x_points - 1)
                base_wave = math.sin(2 * math.pi * freq_x * x / l) + math.sin(2 * math.pi * freq_y * y / w)
                rough_wave = roughness * (math.sin(2 * math.pi * freq_x * 4 * x / l) + math.sin(2 * math.pi * freq_y * 4 * y / w))
                wave = base_wave + rough_wave
                normalized = (wave + 4.0) / 8.0          # safe 0–1 mapping
                z_varying = (h - base_thickness) * normalized
                z = base_thickness + z_varying

                points.add(adsk.core.Point3D.create(x, y, z))

            # Top spline
            spline = sk.sketchCurves.sketchFittedSplines.add(points)

            # Closed profile lines (bottom flat at Z=0, vertical sides)
            p_bottom_left = adsk.core.Point3D.create(0, y, 0)
            p_bottom_right = adsk.core.Point3D.create(l, y, 0)
            p_left_top = points.item(0)
            p_right_top = points.item(points.count - 1)

            sk.sketchCurves.sketchLines.addByTwoPoints(p_bottom_left, p_bottom_right)  # bottom
            sk.sketchCurves.sketchLines.addByTwoPoints(p_bottom_left, p_left_top)      # left vertical
            sk.sketchCurves.sketchLines.addByTwoPoints(p_bottom_right, p_right_top)   # right vertical

            # Add the closed profile to loft list
            profile = sk.profiles.item(0)
            curves.append(profile)

        # Loft into SOLID body
        loftFeats = root.features.loftFeatures
        loftInput = loftFeats.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        for profile in curves:
            loftInput.loftSections.add(profile)
        loftInput.isSolid = True
        loft = loftFeats.add(loftInput)

        # Clean up temporary features (timeline stays tidy)
        for plane in planes_list:
            plane.deleteMe()
        for sk in sketches_list:
            sk.deleteMe()

        ui.messageBox('✅ Solid uneven terrain created!\n\nFlat bottom (parallel to XY plane) at Z=0 — ready for table or 3D print.\nTweak freq_x/freq_y/roughness/base_thickness and rerun.', 'Success')
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))