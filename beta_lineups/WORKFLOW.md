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
- if two objects are identical and aligned, the central line will be displayeed rather than the side one
[Problems :]
- Blue stage : the tip of the arrow head lines are snaping too
### Patch 6
- Correction of the 0.5--0.7  value because buildCoordinates() was affecting the wrong data : a textbox doesn't have a line width
- Reworking hierarkey :
    1. Blue
    2. Green or Pink
- If multiple guidelines can be diisplayed on an axis, it will do
- Blue stage : if triggered, it will avoid other snappings
- try to modify arrow snaping behaviour to save the day
### Patch 7
- Trying to  exclude lines that are drawn by an arrow head from the snaping system
- Giving TEXT_Y_CENTER_FRACTION the right value of 0.6 to finally get the horizontal snaping for text box crossing
- Fixing small line snapping to center of big line in blue stage (bug with blue stage direction
### Patch 7.5
- trying to fix arrow head detection
### Patch 7.6
- Finally exclueding arrow heads from the anchor points relevance using apply_arrow_resize_fix_v2
[Problem]
- In blue stage, the small line will still snap to the center of the big line but this time with the right color (green) (need to exclude that behaviour in blue stage)

**Beyond Patch 7.6, The final patch #10 will need apply_arrow_resize_fix_v2 applied first to function**

### Patch 7.8
### Patch 7.9
- Fixing the smazll line snaping to the middle of the big line under any circumstances

**Todo : a patch gathering v1-v7.9**

## Patches 8.X
Patches 8.X should be independant from another and will implement some brand new features for snaping that can come handy in some case. They are optionnal
### Patch 8.1
Implement equidistant snapping : if 3 objects are on the document, and one of them is selected, a snaping point can be triggered if the selected object happends to be equidistant with the two others. Two arrows will be displayed to signify the equidistance. For the snapping to be triggered, the objects heve to share at least one vertical or horizontal line together (Figma principle)

[Problem :] Missing double arrow display
### Patch 8.1.2
Adding a two-double arrow display
### Patch 8.1.3

**Todo** : Modifying : The left arrow (the one that is the furthest from the selected object, the arrow points to the wrong direction

### Patch 8.2
The guideline is splitted in two halfs and the color of eatch half will depend on what type of anchor point it points to (pink : a side anchor point, green : a center point.

Without the patch, the guideline will havbe one color and this color will turn green if  a center is involvolved
### Patch 8.2.2
If two objects are further than 5pt from one another, the two halfs xwill appear in the blank space (not cover objects anymore but blank)

**Todo** : if lines are not hor or vertical, the guidelines won't go to the ebd point of the line
### Patch 8.3
If the current page's background is "lined with left margin", a snaping point with a grey guideline will be displayed (a guideline on the margin will be displayed too)

If the current page's background is "lined with right margin", a snaping point with a grey guideline will be displayed (a guideline on the margin will be displayed too).  The snaping point is podsition at the horieontal middle of the page (between the margin and the page)

If the current page's background is any other than those two, the anchor will just be the middle of the page

### Patch 8.4
If a straight line is being drawn and it crosses another line perpendicularly, and the two line are biger than 50pt, a pink 15pt guideline perpendicular to the  line that is being drawn will popup to the origin and to the end 
