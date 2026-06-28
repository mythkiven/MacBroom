"""py2app 入口脚本。

注意：脚本名不能叫 MacBroom.py —— 在 macOS 大小写不敏感文件系统上会与包
`macbroom` 同名冲突，导致整个包被入口脚本覆盖、web 资源丢失。故用 macbroom_app.py，
构建后由 build.sh 把产物重命名为 MacBroom.app。
"""

from macbroom.desktop import main

main()
