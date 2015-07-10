Marmalade Quick C Extension -> Lua Wrapper Generator
====================================================

This script takes a Marmalade C extension as an input and outputs a folder of
C++/Marmalade files that tolua++ can then be pointed at to generate Lua APIs
for Quick. This script is needed because:

- C extensions typically have very long unfriendly static function names and
  for Quick you should give users short friendly names inside a table
- C extensions typically use enums, static callback functions, etc., plus
  non standard types like s3eBool and s3eResult which need converting/
  replacing.

Note that this script is not useful for exposing C++ modules. For those, you
should just put // tolua_begin and // tolua_end comments into the normal
headers and you get Lua bindings for free. You might want to add a .lua wrapper
to change the C++ naming to more friendly Quick/Lua style but only if you're
feeling nice :)


The process for creating a Lua version of a C extension
-------------------------------------------------------

1. Run the script, pointing it at an extension
2. If you're lucky, the wrapper works out of the box! Probably you'll need
   to tweak it, e.g. map enums to strings, register callbacks and
   create Lua events in them, etc.
3. Add the wrapper to Quick and rebuild the engine binaries. See further down.


Using the script
----------------

Call either of:

        python.exe path/to/extension_to_lua.py path/to/myExtensionsFolder
        python.exe path/to/extension_to_lua.py path/to/myExtensionsFolder/h/myExrtension.h

Example:

        c:\Marmalade\7.8.0\s3e\python\python.exe extension_to_lua.py C:\Marmalade\7.8.0\extensions\s3eGameCircle

or

        c:\Marmalade\7.8.0\s3e\python\python.exe extension_to_lua.py C:\Marmalade\7.8.0\extensions\s3eIOSGameCenter\h\s3eIOSGameCenter.h

Outputs:

- Copies any existing version to path/to/myExtensionsFolder/QMyExtension.backup:
-Creates this folder: path/to/myExtensionsFolder/QMyExtension
-Creates these files in that folder:
 - QMyExtension.h - declarations, which tolua++ will use
 - QMyExtension.cpp - definition, you'll probably need to edit this
 - QMyExtension.mkf - project file which you will include in the Quick engine when you rebuild

Things the script does:
- Uses file name "s3eMyExtension.h" to make namespace/lua table "myExtension" (e.g. s3eGameCeircle.h -> gameCircle)
- "IOS" as a prefic becomes lowercase for readability, e.g. s3eIOSGameCenter -> iosGameCenter
- Puts all functions in that namespace/table
- Trims off "s3e" prefix from functions and lower-cases their first letter
- Replaces available() with isAvailable() to match Quick style
- Removes register/unregister functions and puts calls to them inside
  init/itialise/initialize and terminate if they both exist.
  You will need to go implement callbacks that generate Lua events in the .cpp file.
  I'll try to automate this more in a future update.
- If there are register/unregister funcs but no init/terminate, it puts them in new start()/stop() functions
- Replaces what looks like enums with char* strings - you needs to add conversion code (again, could be automated...)
- Adds "FIXME..." comments in cpp whenever it looks like an enum, struct or function pointer is used
- Flags (u)int64 usage. Lua uses double precision numbers which I think will give about 1000 below
  the max value for an int64 for example. You should probably test and might have to add a workaround...

The wrappers will give you a useful starting point and avoid the need to do big
search/replace etc. For trivial extensions, this may work 100% out of the box,
but most likely not!


How to use any wrapper generated with this in Quick
===================================================

Prerequisites
-------------

1. Install Marmalade SDK 7.7 or newer

2. Make sure the QMyExtension folder is on a Marmalade search path:

   Easiest option is to put the project in you main github or projects folder.
   Then, if you haven't already, add that folder to the global search by
   putting the following in < Marmalade >/s3e/s3e-default.mkf:

        options { module_path="path/to/my/github/projects/root" }

   Multiple Marmalade installs can pick up all your wrappers/projects then.
  
   If you dont have a main github folder, you can add just the project:
  
        options { module_path="path/to/QMyExtension" }


Setup: Add and build this wrapper into Quick
--------------------------------------------

1. Edit quick/quickuser_tolua.pkg and add this new line:

        $cfile "path/to/QMyExtension/QMyExtension.h"

2. Edit quick/quickuser.mkf and add the following:

        subproject QMyExtension
   
3. Run quick/quickuser_tolua.bat to generate Lua bindings.

4. Rebuild the Quick binaries by running the script(s):
   quick/build_quick_prebuilt.bat etc.
   
   
Using the wrapper in a Quick game
---------------------------------

Put the original C extension project (not the Quick one) in your game's mkf:

        subproject s3eMyExtension

------------------------------------------------------------------------------------------
(C) 2015 Nick Smith.

All code is provided under the MIT license unless stated otherwise:

 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 THE SOFTWARE.
