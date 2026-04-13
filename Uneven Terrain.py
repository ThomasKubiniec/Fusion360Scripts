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

        # === USER INPUTS FOR BOUNDING BOX ===
        l_input = ui.inputBox('Enter length l (e.g. 1000 mm)', 'Terrain Size', '1000 mm')[0]
        w_input = ui.inputBox('Enter width w (e.g. 600 mm)', 'Terrain Size', '600 mm')[0]
        h_input = ui.inputBox('Enter max height h (e.g. 150 mm)', 'Terrain Size', '150 mm')[0]

        l = unitsMgr.evaluateExpression(l_input, 'cm')
        w = unitsMgr.evaluateExpression(w_input, 'cm')
        h = unitsMgr.evaluateExpression(h_input, 'cm')

        # === NEW USER PROMPTS FOR SURFACE CURVES ===
        freq_x_input = ui.inputBox('Enter main frequency X (e.g. 2.0 = gentle waves)', 'Surface Curves', '2.0')[0]
        freq_y_input = ui.inputBox('Enter main frequency Y (e.g. 1.5)', 'Surface Curves', '1.5')[0]
        roughness_input = ui.inputBox('Enter roughness (0 = smooth, 0.4–0.7 = uneven navigation challenge)', 'Surface Curves', '0.4')[0]
        intensity_input = ui.inputBox('Enter curvature intensity (0.5 = mild, 1.0 = normal, 2.0 = extreme)', 'Surface Curves', '1.0')[0]

        freq_x = float(freq_x_input)
        freq_y = float(freq_y_input)
        roughness = float(roughness_input)
        intensity = float(intensity_input)

        # === RESOLUTION (edit here if needed) ===
        num_y_sections = 25
        num_x_points = 40

        curves = []
        planes_list = []
        sketches_list = []

        for i in range(num_y_sections):
            y = i * w / (num_y_sections - 1)

            planeInput = root.constructionPlanes.createInput()
            planeInput.setByOffset(root.xZConstructionPlane, adsk.core.ValueInput.createByReal(y))
            plane = root.constructionPlanes.add(planeInput)
            planes_list.append(plane)

            sk = root.sketches.add(plane)
            sketches_list.append(sk)
            points = adsk.core.ObjectCollection.create()

            for j in range(num_x_points):
                x = j * l / (num_x_points - 1)
                base_wave = math.sin(2 * math.pi * freq_x * x / l) + math.sin(2 * math.pi * freq_y * y / w)
                rough_wave = roughness * (math.sin(2 * math.pi * freq_x * 4 * x / l) + math.sin(2 * math.pi * freq_y * 4 * y / w))
                wave = intensity * (base_wave + rough_wave)

                # Safe normalization so surface always stays 0–h (no tilt, fully horizontal overall)
                A = intensity * (2.0 + 2.0 * roughness)  # theoretical max amplitude
                normalized = (wave + A) / (2.0 * A)
                z = h * normalized

                points.add(adsk.core.Point3D.create(x, y, z))

            spline = sk.sketchCurves.sketchFittedSplines.add(points)
            curves.append(spline)

        # Loft → clean surface body
        loftFeats = root.features.loftFeatures
        loftInput = loftFeats.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        for curve in curves:
            loftInput.loftSections.add(curve)
        loftInput.isSolid = False
        loft = loftFeats.add(loftInput)

        # Clean up
        for p in planes_list: p.deleteMe()
        for s in sketches_list: s.deleteMe()

        ui.messageBox('✅ Horizontal uneven surface created!\n\n• Overall orientation is parallel to XY plane (no global tilt)\n• Z varies only from 0 to h\n• Tweak the new prompts and rerun for instant new challenges.', 'Success')
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))