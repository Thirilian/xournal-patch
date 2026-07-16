# Xournal++ patches
for efficiency reasons, I had to do some changes to xournal++'  code to implement some ergonomy improvement features.

Until I share this with xournal++' team, it will remain python patches.


## Important :
- my first work was  a workaround I thought of regarding the equation tool's error handling. I then improved it to allow me to write code in specific uscases I bumped against in my note-taking experience. 
The repo can be found here : https://github.com/Thirilian/xournal_latex_compiling_scripts

  You can install it if you are on a linux machine. I will keep improving this repo too

  The 2nd patch `apply_txt_prefill.py` is only useful if you use the latex-compilation sh script
  
- All of my ergonomy patches are created to suit my needs or fix a behaviour I consider being a bug. I will keep improving this repo as well as the one mentionned above to make Xournal++' use even smoother.
- You should open the Installation.txt file and, once downloaded, **modify it if something doesn't suit your usecase**.
- If you entcounter any issue, have any question or are working in xournalpp's team, feel free to contact me directly (via MP or creating an Issue report just to chat, I don't mind)
  
## How to use
To install all available patches,  download and run the Installation.txt file (it's a script but it was meant to be instructions)
``` shell 
curl -O https://raw.githubusercontent.com/Thirilian/xournal-patch/main/Installation.txt
sudo chmod +x Installation.txt
bash Installation.txt
```
## Note on the lateest build (for apt-based systems)
the apt repository iss late compared to the github repo and so buillding the app from source got me with some new interesting features, st I wanted to mention some of them here.

Modification the behaviour of the "Add/edit Tex equation" : 


Clicking the tool won't do anything anymore. You will have to click a spot of your page to open the integrated editor. When you are done, the Tex formula's image will be generated where you clicked at the begining. 

Warning : the Tex Editor tool will have its own color, to select after selecting the Tex editor tool. It is independent from the textbox's color.

Important : the formula will apear below right from your cursor. This is intentionnal, as it avoids conflict with the behaviour of selecting an existant textbox with the equation tool.
<img width="1179" height="95" alt="image" src="https://github.com/user-attachments/assets/3a8df604-650f-474d-ae54-fe95ff4a261c" />
<img width="1179" height="123" alt="image" src="https://github.com/user-attachments/assets/cf887d07-683f-4b07-a069-f831d6a35246" />


## Content
### Patch #1 : apply_paste_follow_cursor.py
This patch will make any selected object you pasted snap to the cursor until you press left click

<img width="593" height="255" alt="image" src="https://github.com/user-attachments/assets/66110fda-eca4-4d66-9633-af489578814c" />

### Patch #2 : apply_txt_prefill.py
If you select a textbox while having the Tex editor enabled, the Tex window will open, filled with the con,tent of your texttbox wrapped into "\tex{...}", wich is great in most cases but is not optimal if you wan to directly convert something you wrote in plain text with math mode in it (see example).

This patch uses the "%txt" option provided by my latex compiling script (see repo above) to start the internal editor in plain text mode, allowing you to convert formulas written in a textbox with ease.

**Examples :**

<img width="705" height="23" alt="image" src="https://github.com/user-attachments/assets/74fb288d-e434-40cc-8abe-2a553d3f0efc" />

<img width="333" height="83" alt="image" src="https://github.com/user-attachments/assets/5018d90f-a2c8-42b8-ac9e-198f02d0e9f5" />

<img width="705" height="105" alt="image" src="https://github.com/user-attachments/assets/36773128-1877-4ec7-9e79-e0fb69510ad0" />

________________________________________________________________________________________________________

<img width="583" height="40" alt="image" src="https://github.com/user-attachments/assets/d115b3c8-07bc-46b1-8a92-f5b11e3238eb" />

_selecting the textbox with the equation tool_

<img width="329" height="295" alt="image" src="https://github.com/user-attachments/assets/f7bd4ace-b995-4f55-97cb-3ef1de4fd7e0" />

_tadaaa_ :

<img width="516" height="35" alt="image" src="https://github.com/user-attachments/assets/57c2ed1b-4937-4347-aed7-a7373fdf8c8e" />


### Patch #3 : apply_resize_ratio_v3.py
A new formula will apear as a Tex image with the required size, if it is created from scratch. But if you modify a one-line formula to a two lined formula (simply adding a \dfrac in your original x^2 formula), the formula will shrink because the box wasn't modified.

With this script, the size of the image will be recalculated when editing a formula, to preserve the image size while preserving a potential personalised ratio customized from the user. It will take into acount the size of the pdf befor and after edition, as well as the size of the box before edition to rescale it if needed.

Special case for textboxes. If editing starting from a textbox, the formula box's scale will be ajusted to make the text just as big as the text in the textbox originally was. This considers 12pt to be the "normal fontsize" to wich the formula would be generated with a normal scale.

### Patch #4 : apply_force_recompile.py
Warning : This patch is useless if you use the patch #5, wich already implements this functionnality

When you want to change a tex image's color, you have to change the Tex editor tool's color, open the equation and type something to force recompilation with the correct color.

This patch only implements a unique forced recompilation when you open an existing texbox for edition

### Patch #5 : apply_color_widget_v3.py
This patch adds a wiget allowing the user to change the %%XPP_TEXT_COLOR%% (equation's global color) directly while typing the equation. 

This will force a compilation, so the color is updated on the formula.

<img width="342" height="306" alt="image" src="https://github.com/user-attachments/assets/f11f529a-f8f7-4c9e-b5d8-4caffb2ac719" />
<img width="328" height="306" alt="image" src="https://github.com/user-attachments/assets/6005d1aa-3eb1-47ec-8070-932c95f7934c" />

<img width="506" height="332" alt="image" src="https://github.com/user-attachments/assets/6ad2da7c-b040-44b6-bb24-55822fb8aca2" />


### Patch #6 : apply_floating_marks_v2.py
This patch adds 3 shortcuts to create new shapes. 
**Ctrl+J** create a small hoizontal line for graduation of a y axis. The line will be of the color and width of the curent selected tool. If the current tool is not a drawing tool, the width will fallback to normal. 

**Ctrl+Shift+J** create a small vertical line for graduation of a x axis. The line will be of the color and width of the curent selected tool. If the current tool is not a drawing tool, the width will fallback to normal. 

**Ctrl+K** create a cross to represent a point on a graphic. The cross will be of the color and width of the curent selected tool. If the current tool is not a drawing tool, the width will fallback to normal. 

When using any of these shortcuts, the symbol will snap to the mouse cursor until you press Left click, just like when pasting after using patch #1.



Usecase example :

<img width="838" height="510" alt="image" src="https://github.com/user-attachments/assets/2c859fc3-b094-432b-9f73-e460259d7f07" />


### Patch #7 : apply_arrow_resize_fix_v2.py
When an arrow is created, its head(s) are scaled correctly but because the arrow tool basically draws the heads by tracing two lines automaticaly attatched to the main line, if an existing arrow is being asymetrically rescailed, the head will apear stretched.

For this patch, it was required to add a special marker `arrow="single"` or `arrow="double"` tag in the xopp's xml code for eatch drawn arrow, to be able to differenciate lines, arrows and double arrows and then call the ArrowHandler function (respoonsible for drawing arrows heads) anew on the stroke when it is being unselected

So now, rescaling an arrow will have no visible effect on its head(s)

**Before :**

<img width="433" height="95" alt="image" src="https://github.com/user-attachments/assets/14cd75ec-b61e-40fe-b47d-469a76c7a02e" />

rescaled :

<img width="433" height="95" alt="image" src="https://github.com/user-attachments/assets/e02ad67f-eedd-46f6-b02d-e13b32973642" />


**After :**

<img width="433" height="95" alt="image" src="https://github.com/user-attachments/assets/14cd75ec-b61e-40fe-b47d-469a76c7a02e" />

rescaled :

<img width="433" height="95" alt="image" src="https://github.com/user-attachments/assets/559c9fe4-425c-4cf5-a448-8849abd2db56" />


### Patch #8 : apply_fix_warnings.py
Note : Because it hasn't been reviewed yet, this patch is deactivated in the standard `Installation.txt` file

This patch just fixes the warnings that are currently generated while building the fresh xournalapp clone.

### Patch #9 : apply_fine_arrow_move.py
**__This patch is related to ergonomic changes and is not meant to pe implemented to the xournal official code.__**

When selected, an object can be moved using arrow keys with the following modulations :
**Alt+Arrow key** movement with a 1-point step

**Arrow key** movement with a 3-points step

**Shift+Arrow key** movement with a 10-points step


This patch rebinds Alt+Arrow key and adds a finer movement stage. Here are the new movement controls after aplying this patch :

**Alt+Arrow key** movement with a 0.5-point step

**RightCtrl+Arrow key** movement with a 1-point step

**Arrow key** movement with a 3-points step

**Shift+Arrow key** movement with a 10-points step

### Patch #10 : 
This patch adds the option in the edition menu to enable/disable object snaping, wich will allow for moving objects with alignment guides.

<img width="308" height="81" alt="image" src="https://github.com/user-attachments/assets/c8527f85-a866-4b2c-bdb5-1a6b5ac6de0f" />

This patch also adds a pannel to the preferences window to enable which sub function of this patch will be enabled for you.

________________________________________________________________________________________________________
**All different functionnalities of this feature :**
- basic snaping concept :

Every existing object has 9 "snaping points". When two snaping points are aligned on the X or Y axis, the moving object will be snaped and a two sided guideline will apear to indicate you of such. 
<img width="351" height="240" alt="image" src="https://github.com/user-attachments/assets/f0d108bb-1196-4210-8f10-02c08c7698af" />
<img width="313" height="188" alt="image" src="https://github.com/user-attachments/assets/c048c14e-6c47-4594-a1ce-ebc34d854fcf" />

A guideline reaching the snaping point at the extremity of an object will apear in magenta. 

<img width="311" height="202" alt="image" src="https://github.com/user-attachments/assets/932342a4-f1ed-4eb3-82fb-32d76660a160" />

A guideline reaching the snaping point at the X or Y center of an object will apear in green.

<img width="262" height="275" alt="image" src="https://github.com/user-attachments/assets/2322d3e7-8b6d-481d-8f87-12bef202f66a" />

If a small line (shorter than 15pt by default) crosses a long perpendicular line, a blue guideline will apear and you'll be able to slide the small line across the long line or to snap the small to the long one's extremuties. This is the start of a "graduation assist" functionnality

<img width="807" height="131" alt="image" src="https://github.com/user-attachments/assets/ef1417f3-2df5-4aac-942d-18aabdf1e074" />

<img width="807" height="131" alt="image" src="https://github.com/user-attachments/assets/f9b9d216-88c3-4bd6-a9b8-b5024dca8430" />

________________________________________________________________________________________________________
- <img width="150" height="26" alt="image" src="https://github.com/user-attachments/assets/ca03117f-9162-4569-8b84-0ad4e7b2efd8" />

if three moved objects are equidistant on an axis and are at least partially at the same position on an axis, pink double arrows will apear to signify an equidistant snaping.

<img width="922" height="287" alt="image" src="https://github.com/user-attachments/assets/90144d9f-d9a1-443e-9461-b3a4320744e3" />

________________________________________________________________________________________________________
- <img width="166" height="27" alt="image" src="https://github.com/user-attachments/assets/b4d64960-13b6-4050-b028-b48cd0684d4b" />

will display a grey vertical line to snap to the center of the page. Adapts to the margin if present.

<img width="310" height="280" alt="image" src="https://github.com/user-attachments/assets/48910280-75b0-4995-8f16-745d68fc1c48" />
<img width="310" height="280" alt="image" src="https://github.com/user-attachments/assets/075734cc-024d-48b0-8a8d-ce42d152e7c6" />
<img width="310" height="280" alt="image" src="https://github.com/user-attachments/assets/103f4f0c-b5f2-4469-8914-a8c0000b551d" />

________________________________________________________________________________________________________
- <img width="106" height="25" alt="image" src="https://github.com/user-attachments/assets/b96af6f0-ff11-49e9-966d-bc21594a9f21" />

Will display guidelines while you draw to help you if you want to draw a perfect circle from the elipse tool

<img width="164" height="172" alt="image" src="https://github.com/user-attachments/assets/039882e8-51df-4673-9c8d-2efa64694639" />

________________________________________________________________________________________________________
- <img width="174" height="25" alt="image" src="https://github.com/user-attachments/assets/6fb36f77-d40a-4e93-8ec1-a18470f61112" />

**If you have one graduation (small line shorter than 15pt) snapped to a long line**

then you can slide it freely as shown above

**If you have two graduations of the same size snapped to a long line**

then sliding one will make small guidelines apear on the long line. These small guidelines will be perpendicular to the long line and the same lenght as the two small lines. The small guidelines will be equidistant from eachother depending on the distance you set between the two existing graduation.

<img width="838" height="110" alt="image" src="https://github.com/user-attachments/assets/f454aaa1-9758-4508-923f-5acac0311ac1" />

**If you have three or more graduations of the same size snapped to a long line**

... and you are trying to snap a new one to the long line, all "slots" will be displayed and the new small line will be forced to snap at one

<img width="838" height="110" alt="image" src="https://github.com/user-attachments/assets/29fe44e4-45f5-4490-a565-a0c41ef7a2b8" />

**If you have three or more graduations of the same size snapped to a long line, but you managed to make them non-equidistant**

moving or snaping a new graduation of that size will fallback to the first usecase (you can slide the graduation where you want on the long line), but the long line will have a red guideline to indicate you are in this "error-fallback" case

<img width="838" height="110" alt="image" src="https://github.com/user-attachments/assets/cf7a5e78-7a8f-4daa-8f20-e4893c356836" />

________________________________________________________________________________________________________
- <img width="180" height="28" alt="image" src="https://github.com/user-attachments/assets/d23c3487-2896-4640-85fb-258ad8ea3efb" />

whenever moving a graduation, you can "dffrag it" to the top or bottom side of the long line. This would make the blue guideline and the graduation you are moving "move up" or "move down". If you are letting go of the graduation when it's in a new state, every graduation of the same size will be moved to follow the direction of the graduation you dragged

<img width="826" height="118" alt="image" src="https://github.com/user-attachments/assets/08263130-6680-41e4-9d75-b0410ab74250" />

<img width="826" height="118" alt="image" src="https://github.com/user-attachments/assets/e41b966e-f28d-42df-80f4-cdb8ea761b21" />

<img width="826" height="118" alt="image" src="https://github.com/user-attachments/assets/a14c4763-3cd0-4293-98a0-571f6a528b15" />

(a graduation can still be unsnapped if dragging further)

(all of these operations can be performed on horizontal graduations snapped onto a vertical long line as well)

________________________________________________________________________________________________________
- <img width="213" height="29" alt="image" src="https://github.com/user-attachments/assets/364c1373-e9bb-476b-a828-b2118c064b8b" />

Trying to move 
- a textbox
- a Tex formula box
- an image

in the square of a table will make yellow guidelines appear to show when the content is centered on the X or Y axis of this square

<img width="838" height="461" alt="image" src="https://github.com/user-attachments/assets/587a792f-1bf8-4890-9b34-0d0d61a938c9" />

(it also works on 3-sided table squares) 
<img width="856" height="461" alt="image" src="https://github.com/user-attachments/assets/7f78fbec-2310-4be3-a5ca-cc8d6a36f323" />

- <img width="221" height="29" alt="image" src="https://github.com/user-attachments/assets/d52b2cfc-cd43-42a9-ab75-eaab968219ef" />

while drawing a spline, its moving point can snap to evrey guideline possible.

<img width="560" height="420" alt="image" src="https://github.com/user-attachments/assets/a3578231-8a58-4901-841e-eb56e307bd07" />

________________________________________________________________________________________________________
**A lot of settings of this feature can be tweakeed in the new available pannel called "Snapping" in the preferences window that patch #10 is adding**

### Patch #11 : apply_force_line_style_update_v2.py
So far, if you select a line style from the pen tool to update the line type of a selected object, and the line style you clicked is already selected by the tool, the line style of the object isn't updated. You have to select a different line style for the tool and reselect the style you wanted for the object to update.

this patch fixes that.

<img width="161" height="153" alt="image" src="https://github.com/user-attachments/assets/e28e9260-608e-44e0-a561-febaab585b68" />

### Patch #12 : apply_table_writing_assist.py
when creating a textbox in a table's square, it spawns centered in that square.

If the textbox overflows boundaries, the text's size will lower until reaching 6pt.

Using the arrow keys you can navigate the squares in a table wich will either create a centered textbox or open the textbox which is already in a nearby square.

<img width="822" height="483" alt="image" src="https://github.com/user-attachments/assets/a14c97bf-e36c-4be8-ad88-9833dbe0aafc" />

<img width="822" height="483" alt="image" src="https://github.com/user-attachments/assets/87877e1f-0bd2-4b79-95f4-165ed93ab5b6" />


(not done yet, future functionnality) using Ctrl+ Arrow key, you can navigate between textboxes even faster

**case of "vertical tables**
If a table is exclusively composed of **multiple vertical lines** all crossed my **one unique horizontal line**, this feature will create "slots" acordingly.

The hight of these slots will depend on the "hight" of the first row.

<img width="308" height="589" alt="image" src="https://github.com/user-attachments/assets/23a28d13-f86f-471a-9451-912a48def38e" />

### Patch 13 : apply_latex_completion.py
offers a completion feature when you type in the Tex window. 

The dictionary of completable termes can be customized through the LaTeX menu in the Preferences window.

You can also decide if (and which) placeholders will be placed after the command you typed, if this one contained placeholders, to help you navigate faster.

You can use Tab/Shift+Tab to navigate between placeholders in the formula.

The completion popup can be closed manually when pressing F1

<img width="344" height="175" alt="image" src="https://github.com/user-attachments/assets/b7d7a4a2-c4e5-4653-af2a-ce1da3049000" />
<img width="344" height="229" alt="image" src="https://github.com/user-attachments/assets/dcbb2f71-27ed-446c-aab9-00f90ab0fdec" />
<img width="344" height="229" alt="image" src="https://github.com/user-attachments/assets/30309ece-ebcf-443c-99f0-8875ec96cc3e" />

<img width="1018" height="222" alt="image" src="https://github.com/user-attachments/assets/eab44292-6632-4d87-b3d1-8e14f6b23aa4" />

### Patch 14 : apply_no_popup_during_typing.py
prevent any popup to apear and catch the focus wwhile you are typing through the Tex window

### Patch 15 : apply_no_popup_during_typing.py
(this patch requires apply_floating_marks_v2.py and apply_paste_follow_cursor.py to be applied before it)

with this patch, you can use Ctrl+L to make an arrow head (one-pieced object) spawn on the page, snapping to the cursor by default just like for patch #6.

By default, this arrowhead will point upwards. 

If this arrowhead is moved to a stroke of any kind, it will snap to it, pointing in the same direction (tangeant). It will point in a specific way (by default, ]-90°;+90°]). When selected, an arrow head can be flipped by 180° pressing "R".

<img width="290" height="222" alt="image" src="https://github.com/user-attachments/assets/f8666f07-b98f-4d76-a63a-04bdb8c130e2" />
<img width="139" height="123" alt="image" src="https://github.com/user-attachments/assets/0f4adb21-5623-4bde-9069-3bd6bef0e5b9" />
<img width="509" height="123" alt="image" src="https://github.com/user-attachments/assets/0c695a4e-3222-443a-82c7-c620ef5094ea" />
<img width="588" height="248" alt="image" src="https://github.com/user-attachments/assets/e094fe88-edd2-42cf-b38d-83cbd55bfdaf" />

<img width="139" height="123" alt="image" src="https://github.com/user-attachments/assets/ecb337ad-97e0-41ea-ada9-d9b5e3a1f8bc" />

An arrowhead which has been flipped once will point downwards by default ([-90°;+90°[)

## Contact me
- if you are from xournalpp team and would like to implement one of these features into the actual current source code (please don't implement one of these features without contacting me first)
- if you have any question whatsoever
- if you have a suggestion to make
- if you encounter any issue related to one of the patches, the building process or the installation
- if you see a typo or an issue (missing clarity ?) in the readme

You can contact me
- by creating an issue report (I don't mind, even if it's just to chat)
- by creating a discussion topic
- via mps
