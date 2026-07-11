# xournal++ patches
for efficiency reasons, I had to do some changes to xournal++'  code to implement some ergonomy improvement features.

Until I share this with xournal++' team, it will remain python patches.


## Important :
- my first work was  a workaround I thought of regarding the equation tool's error handling. I then improved it to allow me to write code in specific uscases I bumped against in my note-taking experience. 
The repo can be found here : https://github.com/Thirilian/xournal_latex_compiling_scripts

  You can install it if you are on a linux machine. I will keep improving this repo too

  The 2nd patch `apply_txt_prefill.py` is only useful if you use the latex-compilation sh script
  
- All of my ergonomy patches are related to LaTeX formula usage. I will keep improving this repo as well as the one mentionned above to make LaTeX' integration even smoother.
- You should open the Installation.txt file and, once downloaded, **modify it if something doesn't suit your usecase**.
- If you entcounter any issue, have any question or are working in xournalapp's team, feel free to contact me directly (via MP or creating an Issue report just to chat, I don't mind)
  
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

<img width="402" height="82" alt="image" src="https://github.com/user-attachments/assets/08ae0c61-fd33-4e33-9fe9-258ba7508d45" />

This patch also adds a pannel to the preferences window to enable which sub function of this patch will be enabled for you.

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

- <img width="150" height="26" alt="image" src="https://github.com/user-attachments/assets/ca03117f-9162-4569-8b84-0ad4e7b2efd8" />

if three moved objects are equidistanton an axis and are at least partially at the same position on an axis, pink double arrows will apear to signify an equidistant snaping.

<img width="922" height="287" alt="image" src="https://github.com/user-attachments/assets/90144d9f-d9a1-443e-9461-b3a4320744e3" />

- <img width="166" height="27" alt="image" src="https://github.com/user-attachments/assets/b4d64960-13b6-4050-b028-b48cd0684d4b" />

will display a grey vertical line to snap to the center of the page. Adapts to the margin if present.

<img width="838" height="757" alt="image" src="https://github.com/user-attachments/assets/48910280-75b0-4995-8f16-745d68fc1c48" />
<img width="838" height="757" alt="image" src="https://github.com/user-attachments/assets/075734cc-024d-48b0-8a8d-ce42d152e7c6" />
<img width="838" height="757" alt="image" src="https://github.com/user-attachments/assets/103f4f0c-b5f2-4469-8914-a8c0000b551d" />

- Circle assist
Will display guidelines while you draw to help you if you want to draw a perfect circle from the elipse tool

<img width="164" height="172" alt="image" src="https://github.com/user-attachments/assets/039882e8-51df-4673-9c8d-2efa64694639" />



### Patch #11 : apply_force_line_style_update_v2.py
So far, if you select a line style from the pen tool to update the line type of a selected object, and the line style you clicked is already selected by the tool, the line style of the object isn't updated. You have to select a different line style for the tool and reselect the style you wanted for the object to update.

this patch fixes that.
### Patch #12 : apply_table_writing_assist.py
when creating a textbox in a table's square, it spawns centered in that square.

If the textbox overflows boundaries, the text's size will lower until reaching 6pt.

(to come) using the arrow keys you can navigate the squares in a table wich will either create a centered textbox or open the textbox which is already in a nearby square.

Using Ctrl+ Arrow key, you can navigate between textboxes even faster

### Patch 13 : apply_latex_completion.py
offers a completion feature when you type in the Tex window. The dictionary of completable termes can be customized through the LaTeX menu in the Preferences window.

The completion popup can be closed manually when pressing F1

### Patch 14 : apply_no_popup_during_typing.py
prevent any popup to apear and catch the focus wwhile you are typing through the Tex window

