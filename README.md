xournal++ patches
for efficiency reasons, I had to do some changes to xournal++'  code to implement some ergonomy improvem ent features
until I share this with xournal++' team, it will remain python patches.

Content
Important :
- my first work was  a workaround I thought of regarding the equation tool's error handling. I then improved it to allow me to write code in specific uscases I bumped against in my note-taking experience. 
The repo can be found here : https://github.com/Thirilian/xournal_latex_compiling_scripts
You can install it if you are on a linux machine. I will keep improving this repo too
The 2nd patch `apply_txt_prefill.py` is only useful if you use the latex-compilation sh script
- All of my ergonomy patches are related to LaTeX formula usage. I will keep improving this repo as well as the one mentionned above to make LaTeX' integration even smoother.
- You should open the Installation.txt file and, once downloaded, **modify it if something doesn't suit your usecase**.
- If you entcounter any issue, have any question or are working in xournalapp's team, feel free to contact me directly (via MP or creating an Issue report just to chat, I don't mind)

How to use
To install all available patches,  download and run the Installation.txt file (it's a script but it was meant to be instructions)
```
https://github.com/Thirilian/xournal-patch/blob/main/Installation.txt
sudo chmod 677 Installation.txt
bash Installation.txt
```

Patches :
Patch #1 : apply_follow_cursor.py
This patch will modify the behaviour of the "Add/edit Tex equation" : 
Clicking the tool won't do anything anymore. You will have to click a spot of your page to open the integrated editor. When you are done, the Tex formula's image will be generated where you clicked at the begining. 
Important : the formula will apear below right from your cursor. This is intentionnal, as it avoids conflict with the behaviour of selecting an existant textbox with the equation tool.
<img width="1179" height="95" alt="image" src="https://github.com/user-attachments/assets/3a8df604-650f-474d-ae54-fe95ff4a261c" />
<img width="1179" height="123" alt="image" src="https://github.com/user-attachments/assets/cf887d07-683f-4b07-a069-f831d6a35246" />

Patch #2 : apply_txt_prefill.py
If you select a textbox while having the Tex editor enabled, the Tex window will open, filled with the con,tent of your texttbox wrapped into "\tex{...}", wich is great in most cases but is not optimal if you wan to directly convert something you wrote in plain text with math mode in it (see example).
This patch uses the "%txt" option provided by my latex compiling script (see repo above) to start the internal editor in plain text mode, allowing you to convert formulas written in a textbox with ease.

Patch #3 : 
A new formula will apear as a Tex image with the required size, if it is created from scratch. But if you modify a one-line formula to a two lined formula (simply adding a \dfrac in your original x^2 formula), the formula will shrink because the box wasn't modified.
With this script, the size of the image will be recalculated when editing a formula, to preserve the image size while preserving a potential personalised ratio customized from the user. It will take into acount the size of the pdf befor and after edition, as well as the size of the box before edition to rescale it if needed.
Special case for textboxes. If editing startinfgf from a textbox, the formula box's scale will be ajusted to make the text just as big as the text in the textbox originally was. This considers 12pt to be the "normal fontsize" to wich the formula would be generated with a normal scale.
