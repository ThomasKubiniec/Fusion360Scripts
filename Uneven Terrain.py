import adsk.core, adsk.fusion, traceback, math

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('No active design.')
            return
        root = design.rootComponent
        unitsMgr = design.unitsManager

        # === BOUNDING BOX INPUTS ===
        l_input = ui.inputBox('Enter length l (X direction, e.g. 1000 mm)', 'Terrain Size', '1000 mm')[0]
        w_input = ui.inputBox('Enter width w (Y direction, e.g. 600 mm)', 'Terrain Size', '600 mm')[0]
        h_input = ui.inputBox('Enter max height h (Z variation, e.g. 150 mm)', 'Terrain Size', '150 mm')[0]

        l = unitsMgr.evaluateExpression(l_input, 'cm')
        w = unitsMgr.evaluateExpression(w_input, 'cm')
        h = unitsMgr.evaluateExpression(h_input, 'cm')

        # === CURVE CONTROL INPUTS (new prompts as requested) ===
        freq_x_input = ui.inputBox('Main frequency X (e.g. 2.0 = gentle waves along length)', 'Curve Controls', '2.0')[0]
        freq_y_input = ui.inputBox('Main frequency Y (e.g. 1.5)', 'Curve Controls', '1.5')[0]
        roughness_input = ui.inputBox('Roughness (0 = smooth, 0.4 = moderate uneven, 0.7 = challenging for robot)', 'Curve Controls', '0.4')[0]
        intensity_input = ui.inputBox('Curvature intensity (0.5 = mild, 1.0 = normal, 2.0 = extreme)', 'Curve Controls', '1.0')[0]
        min_z_input = ui.inputBox('Minimum Z offset (enter 0 for flat lowest point at Z=0)', 'Curve Controls', '0')[0]

        freq_x = float(freq_x_input)
        freq_y = float(freq_y_input)
        roughness = float(roughness_input)
        intensity = float(intensity_input)
        min_z_offset = float(min_z_input)

        # Resolution (stable defaults)
        num_y_sections = 25
        num_x_points = 40

        curves = []
        planes_list = []
        sketches_list = []

        for i in range(num_y_sections):
            y = i * w / (num_y_sections - 1)

            # Offset plane parallel to XZ (Y = constant)
            planeInput = root.constructionPlanes.createInput()
            planeInput.setByOffset(root.xZConstructionPlane, adsk.core.ValueInput.createByReal(y))
            plane = root.constructionPlanes.add(planeInput)
            planes_list.append(plane)

            sk = root.sketches.add(plane)
            sketches_list.append(sk)
            points = adsk.core.ObjectCollection.create()

            for j in range(num_x_points):
                x = j * l / (num_x_points - 1)

                # Parametric waves — purely vertical Z variation (no tilt)
                base_wave = math.sin(2 * math.pi * freq_x * x / l) + math.sin(2 * math.pi * freq_y * y / w)
                rough_wave = roughness * (math.sin(2 * math.pi * freq_x * 4 * x / l) + math.sin(2 * math.pi * freq_y * 4 * y / w))
                wave = intensity * (base_wave + rough_wave)

                # Normalize to exact 0..h range with user-controlled min offset
                A = intensity * (2.0 + 2.0 * roughness)   # safe amplitude estimate
                normalized = (wave + A) / (2.0 * A)
                z = min_z_offset + h * normalized

                points.add(adsk.core.Point3D.create(x, y, z))

            spline = sk.sketchCurves.sketchFittedSplines.add(points)
            curves.append(spline)

        # Loft surface (horizontal overall)
        loftFeats = root.features.loftFeatures
        loftInput = loftFeats.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        for curve in curves:
            loftInput.loftSections.add(curve)
        loftInput.isSolid = False
        loft = loftFeats.add(loftInput)

        # Clean timeline
        for p in planes_list: p.deleteMe()
        for s in sketches_list: s.deleteMe()

        ui.messageBox('✅ Horizontal uneven surface created!\n\n• Z varies only vertically (overall surface parallel to XY plane)\n• Use new prompts to tune waves & roughness\n• For 3D print: sketch l×w rectangle on XY plane, extrude ~20 mm base, Thicken surface downward 20 mm, then Combine.', 'Success')
    except Exception as e:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))