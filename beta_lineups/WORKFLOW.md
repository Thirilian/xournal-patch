# Snap patch
Patch #10 is pretty ambitious so I am working on it by adding sub-patches that add up layer by layer to hopefully get to a satisfying result where I can merge all of the sub patches into one big patch with every functionnality in one patch.

This folder is a working directory where I post every ready-to-use patch that is part of the big patch 10 functionality : snaping guidelines.

### Patch 1
Testing if the snaping between two objects is functionnal : 

[Effect :] If an object is selected and moved towards another still object, the snaping will ocure. No guidelines are drawn yet because it is a proof of concept

### Patch 2
Adding visible guidelines to visualize the origin of a snapping between two ancor points of two different objects

[Effect :] 
- If two objects are snapped, a pink guideline is drawn between the two anchor points
- Option in Edit menu : Enable. disable snaping functions

[Problems :] 

- horizontal and vertical strokes do have 9 anchor points ; the width of the line creates 3 ancor points instead of one

<img width="613" height="34" alt="image" src="https://github.com/user-attachments/assets/b1bda879-8b3f-4883-8199-db8d7db3da8f" />

<img width="613" height="34" alt="image" src="https://github.com/user-attachments/assets/64152e0e-ad05-4cb4-9065-4dafc29ca012" />

<img width="613" height="34" alt="image" src="https://github.com/user-attachments/assets/4a799cdc-68bc-4ae8-a719-2d575aed9eac" />

- too many guidelines apear if too many objects are on the screen
- Anchor points on the side of a line are not harmoniously placed :
<img width="299" height="208" alt="image" src="https://github.com/user-attachments/assets/aff4d9ea-58b0-4cb1-95b0-36ccdc201891" />


### Patch 3
[Effects :] 
- A guideline can only be created between two objects that are curently visible on the user's screen
- For every horizontal strokes, only one anchor point is available on the x axis (symetrical goes for vertical strokes)
- If at least one of the two anchor points involved in a snaping is the center of an object, the guideline will apear green instead of pink
- stroke anchor points harmonized beetween selected and placed versions
[Problems :]
- Anchor points on the side of a line are not harmoniously placed

### Patch 4
[Effects :]
- Text guideline in the horizontal middle's height is changed to allow crossing textbox (from 0.5 to 0.7)
- Introducing blue stage with 1.5 times more snaping force : small line perpendicular to a big line
- Anchor points in extremity of a stroke are harmonized between selected and unselected object
- Introduce Ctrl+B keybind to enable/disable the option in Edit menu disabling/enabling all snaping functions
[Problems]
- The change from 0.5 to 0.7 changed the wrong alignement : line (unseeable)
- Blue stage : the small line would snap in the middle of the long line
- Blue stage : to many snaping point prevent from easely snaping to the blue long stroke
### Patch 5
- Restoring  Text factor from 0.7 to 0.5 and specific case for guidelines with textboxes only
- Blue stage gets a higher hierarchy than green and pink :
    1. Blue
    2. Green
    3. Pink
- Blue stage : A line is considered small if it is shorter than 15pt
- Changing color for blue guidelines
