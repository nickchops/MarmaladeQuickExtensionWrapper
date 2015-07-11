'''
Usage: call either of:
python.exe path/to/extension_to_lua.py path/to/myExtensionsFolder
python.exe path/to/extension_to_lua.py path/to/myExtensionsFolder/h/myExrtension.h

Outputs to path/to/myExtensionsFolder/QMyExtension

e.g.
c:\Marmalade\7.8.0\s3e\python\python.exe extension_to_lua.py C:\Marmalade\7.8.0\extensions\s3eGameCircle
or
c:\Marmalade\7.8.0\s3e\python\python.exe extension_to_lua.py C:\Marmalade\7.8.0\extensions\s3eIOSGameCenter\h\s3eIOSGameCenter.h
etc

See readme.md for more info
'''

import os
import sys
import re
import shutil

here = os.path.dirname(__file__)

def main(sourceFile):

    # Try to find header file and source API name
    source_path = sourceFile
    source_folder = source_path
    success = False
    paths_tried = []

    if os.path.exists(source_path):
        success = True
    else:
        paths_tried.append(source_path)
        split_path = re.split("/|\\", sourceFile)
        source_path = os.sep.join(split_path)
        if os.path.exists(source_path):
            success = True
        #else can try to extend search...

    if not success:
        print('Failed to find input path. Tried:')
        for path in source_path:
            print path
        return -1

    source_path = os.path.abspath(source_path) #keep it consistent
    
    root_path, source_api_name = os.path.split(source_path) #either folder or header
    
    # will eventually end up as, for example:
    #     source_path:     blla/blaa/s3eMyExt/h/s3eMyExt.h
    #     root_path:       blla/blaa/s3eMyExt
    #     source_api_name: s3eMyExt

    if os.path.isdir(source_path):
        root_path = source_path
        source_path = os.path.join(source_path, 'h', source_api_name + '.h')
        if not os.path.exists(source_path):
            print('Could not find header, expected: ' + source_path)
            return -1
    else:
        if not source_path.endswith('.h'):
            print('File is not a header (.h): ' + source_path)
            return -1
        else:
            source_api_name = source_api_name[:-2]
            root_path, x = os.path.split(root_path) #lose header folder

    # s3eMyExt -> myExt
    output_api_name = source_api_name

    if output_api_name.startswith('s3e'):
        output_api_name = output_api_name[3:]
    
    if output_api_name.startswith('IOS'):
        output_api_name = 'ios' + output_api_name[3:] # prefer lowercase for readability

    output_api_name = output_api_name[0].lower() + output_api_name[1:]
    
    # Files would be: QMyExt.h and QMyExt.cpp
    output_file_prefix = 'Q' + output_api_name[0].upper() + output_api_name[1:]
    output_file_prefix_upper = output_file_prefix.upper()
    
    output_dir = os.path.join(root_path, output_file_prefix)
    
    backup_dir = output_dir + '.backup'
    if os.path.exists(output_dir) and os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)
        
    if os.path.exists(output_dir):
        os.rename(output_dir, backup_dir)
        
    os.makedirs(output_dir)
    
    mkf = '''
# Simple project to include extension and quick wrapper files

subprojects
{
    ''' + source_api_name + '''
}

files
{
    ''' + output_file_prefix + '''.h
    ''' + output_file_prefix + '''.cpp
}
'''
    
    with open(os.path.join(root_path, output_dir, output_file_prefix + '.mkf'), 'w') as f:
        f.write(mkf)

    # header and footer
    output_api_header_h = '''
#ifndef __''' + output_file_prefix_upper + '''_H
#define __''' + output_file_prefix_upper + '''_H

// tolua_begin

namespace ''' + output_api_name + ''' {
'''

    output_api_footer_h = '''
} //namespace ''' + output_api_name + '''

// tolua_end

#endif // ''' + output_file_prefix_upper + '''_H
'''

    output_api_header_cpp = '''
#include "''' + output_file_prefix + '''.h"
#include "''' + source_api_name + '''.h"
#include "QLuaHelpers.h"
#include "lua.h"

using namespace quick;

namespace ''' + output_api_name + ''' {
'''

    output_api_footer_cpp = '''
} //namespace ''' + output_api_name + '\n'
    
    # Read and process the header using regexs
    input_raw = ''
    with open(source_path, 'r') as f:
        input_raw = f.read()
    
    output_functions_h = ''
    output_functions_cpp = ''
    #TODO output functions should go in a list that can be searched/edited before printing
    #e.g. to insert register/unregister calls if needed
    
    # Get list of all the functions
    funcs_found = re.finditer(r'(\S+)\s+(\S+)\((.*?)\);', input_raw)

    # Find the callbacks enum list
    callbacks = re.search(r'typedef\s+enum\s+(' + source_api_name + r'Callback)\s*\{(.*?)\}', input_raw, re.DOTALL)
    callback_list = []
    callback_type = None
    
    if callbacks:
        callback_type = callbacks.group(1)
        
        # Find all the actual callback names (example: S3E_MYEXTENSION_CALLBACK_NAME_CALLBACK = 0, //comments)
        # These are user deefined so could hae all sorts of names. Do our best to guess...
        callback_names = re.finditer(r'^\s*(.*?)\s*[,=]', callbacks.group(2), re.MULTILINE)
        if callback_names:
            for name_match in callback_names:
                name = name_match.group(1)
                if name.endswith("MAX"):
                    continue
                name_for_func = name.lower()
                name_for_func = name_for_func.replace('s3e', '')
                name_for_func = name_for_func.replace(source_api_name.lower(), '')
                name_for_func = name_for_func.replace(output_api_name.lower(), '')
                name_for_func = name_for_func.replace('callback', '')
                name_for_func = name_for_func.split('_')
                final_name = ''
                
                for part in name_for_func:
                    if len(part) == 0: # "_" -> empty string
                        continue
                        
                    final_name += part[0].upper()
                    if len(part) > 1:
                        final_name += part[1:]
                callback_list.append((name, final_name))
    
    func_reg = None
    func_unreg = None
    
    special_funcs = {'init': None, 'initialise': None, 'initialize': None, 'start': None, 'terminate': None, 'stop': None}
    
    output_list = []
    func_id = 0
    
    for func in funcs_found:
        return_type = func.group(1)
        func_name = func.group(2)
        params = func.group(3)
        s3eResult = False #need to negate logic as 0=success, 1 = fail
        extra_info = ''
        
        if func_name.startswith('('): #function pointers for callbacks
            continue
        
        call_return = 'return '
        original_return_type = return_type
        
        if return_type == "void":
            call_return = ''
        elif return_type.startswith(source_api_name):
            if return_type.endswith('*'):
                extra_info += "\n    //FIXME: Looks like this returns a struct pointer or similar.\n    //Consider adding some custom Lua code to turn struct into a table.\n"
            else:
                extra_info += "\n    //FIXME: Returning a string instead of " + return_type + " - needs converting\n"
                return_type = 'const char*' #Assume its an enum and return a string
        elif return_type == 's3eBool':
            return_type = 'bool'
            call_return += '(bool)'
        elif return_type == 's3eResult':
            return_type = 'bool'
            s3eResult = True
        elif return_type == 'int64' or return_type == 'uint64':
            extra_info += "\n    //WARNING: Returning a " + return_type + " - This may have issues if the\n    //potential range is outside of the max/min values Lua can represent!\n    //Lua 5.1 uses double precision floats for numbers, which gives about 1000 below\n    //the max value for an int64 when using integers, for example\n"
        # else leave as is for user to fix if needed
        # int, double, etc are valid (-> number)
        # char* and const char* are valid (-> string)
        
        # [^*\s,] matches anything apart from whitespace, comma or * (for pointers where * is
        # declared next to the name instead of type)
        params_found = re.finditer(r'(.+?)([^*\s,]+)(,|$)', params)
        params = ''
        param_list = []
        call_params = ''
        for param in params_found:
            param_type = param.group(1).strip()
            param_name = param.group(2).strip()
            param_list.append((param_type,param_name))
            
            if param_type.startswith(source_api_name):
                if param_type.endswith('CallbackFn'):
                    extra_info += "\n    //FIXME: Looks like '" + param_name + "' is a callback pointer.\n    //Consider an event/callback registered in init function instead\n"
                elif param_type.endswith('*'):
                    extra_info += "\n    //FIXME: Looks like '" + param_name + "' is a callback or struct pointer.\n    //Consider an event/callback registered in init instead\n    //Or add some custom Lua code to turn struct into a table.\n"
                else:
                    #assume this is an enum -> should accept strings and convert.
                    # todo: in cpp add a switch that compares strings and passes enums
                    param_type = "const char*" #char converts cheaper in tolua than String
            elif param_type == 's3eBool':
                param_type = 'bool'
            elif param_type == 's3eResult': #TODO, need to change calling code (in call_params) to negate this!
                param_type = 'bool'
            elif param_type == 'int64' or param_type == 'uint64':
                extra_info += "\n    //WARNING: Param " + param_name + " uses " + param_type + " - This may have issues if the\n    //potential range is outside of the max/min values Lua can represent!\n    //Lua 5.1 uses double precision floats for numbers, which gives about 1000 below\n    //the max value for an int64 when using integers, for example.\n"
            if len(params) > 0:
                params = params + ', '
                call_params = call_params + ', '

            params = params + param_type + ' ' + param_name
            call_params = call_params + param_name
        
        # Callback register should be handled quietly in init/start and stop/terminate functions
        # For now, we'll just print these hints into the init and terminate functions,
        # But eventually should automate this completely
        if func_name == source_api_name + "Register":
            func_reg = "//Register all callbacks here:"
            reg_type, reg_name = param_list[0]
            
            if reg_type == callback_type:
                for callback_info in callback_list:
                    callback_id, callback_fn = callback_info
                    func_reg += '\n    ' + func_name + '(' + callback_id + ', ' + callback_fn + 'Callback, NULL);'
            
            continue
        
        if func_name == source_api_name + "UnRegister":            
            func_unreg = "//Un-register all callbacks here:"
            reg_type, reg_name = param_list[0]
            
            if reg_type == callback_type:
                for callback_info in callback_list:
                    callback_id, callback_fn = callback_info
                    func_unreg += '\n    ' + func_name + '(' + callback_id + ', ' + callback_fn + 'Callback);'
            continue
            
        func_name_lua = func_name
        
        if func_name.startswith(source_api_name):
            func_name_lua = func_name_lua[len(source_api_name):]
        
        func_name_lua = func_name_lua[0].lower() + func_name_lua[1:]
        
        if func_name_lua == 'available':
            func_name_lua = 'isAvailable'
        
        for funcKey in special_funcs:
            if func_name_lua == funcKey:
                special_funcs[funcKey] = func_id
        
        # May want to look for functions that have char* (non const) params and put a
        # note on how that will become a multiple return value!
        
        output_list.append({'return_type': return_type, 'call_return': call_return, 'func_name': func_name, 'func_name_lua': func_name_lua, 'params': params, 'call_params': call_params, 'original_return_type': original_return_type})
        
        if len(extra_info) > 0:
            output_list[func_id]['extra_info'] = extra_info
        
        func_id += 1
    
    # Reg/unreg either go:
    # - in init() and terminate() if both exists
    # - in start() and stop() if either of the above is missing, in which case
    # - new start and/or stop functions are added if they don't already exist
    got_init = False
    if func_reg:
        reg_key = None
        if special_funcs['init']:
            reg_key = special_funcs['init']
            got_init = True
        elif special_funcs['initialise']:
            reg_key = special_funcs['initialise']
            got_init = True
        elif special_funcs['initialize']:
            reg_key = special_funcs['initialize']
            got_init = True
        
        if got_init and not special_funcs['terminate']:
            got_init = False
            
        if not got_init and special_funcs['start']:
            reg_key = special_funcs['start']
        elif not got_init:
            new_entry = {'func_name_lua': 'start', 'params': '', 'return_type': 'void'}
            if reg_key: # init func was found -> insert after it
                reg_key += 1
                output_list.insert(reg_key, new_entry)
            else:
                reg_key = func_id # end of list
                output_list.append(new_entry)
                #TODO: better to put after available or at top if neither (that prob shouldnt happen though!)

        output_list[reg_key]['register'] = func_reg
        
    if func_unreg:
        unreg_key = None
        if got_init and special_funcs['terminate']:
            unreg_key = special_funcs['terminate']
        elif special_funcs['stop']:
            unreg_key = special_funcs['stop']
        else:
            new_entry = {'func_name_lua': 'stop', 'params': '', 'return_type': 'void'}
            if reg_key:
                unreg_key = reg_key+1
                output_list.insert(unreg_key, new_entry)
            else:
                unreg_key = func_id
                output_list.append(new_entry)
            
        output_list[unreg_key]['register'] = func_unreg
    
    if len(callback_list) > 0:
        output_functions_cpp += '\n//------------------------------------------------------------------------------\n//C++ callbacks -> Lua events:\n'
        
        for callback_info in callback_list:
            callback_id, callback_fn = callback_info
            output_functions_cpp += '''
int32 ''' + callback_fn + '''Callback(void* systemData, void* userData)
{
    LUA_EVENT_PREPARE("''' + output_api_name + '''");
    LUA_EVENT_SET_STRING("type", "''' + callback_fn.lower() + '''");
    //LUA_EVENT_SET_BOOLEAN("???", ???);
    //LUA_EVENT_SET_STRING("???", ???);
    //LUA_EVENT_SET_INTEGER("???", ???);
    LUA_EVENT_SEND();
    lua_pop(g_L, 1);

    return 0;
}
'''
    
    output_functions_cpp += '\n//------------------------------------------------------------------------------\n//Functions:\n'
    
    for values in output_list:
        output_function = values['return_type'] + ' ' + values['func_name_lua'] + '(' + values['params'] + ')'
        
        out_pre = '\n    '
        func_called_so_return_this = False
        
        output_functions_h += out_pre + output_function + ';'
        output_functions_cpp += '\n' + output_function + '\n{'
        
        if 'register' in values:
            if 'func_name' in values and values['original_return_type'] == 's3eResult':
                output_functions_cpp += out_pre + 'if(' +  values['func_name'] + '(' + values['call_params'] + ') == S3E_RESULT_ERROR)' + out_pre + '    return false;\n'
                func_called_so_return_this = 'true'
        
            output_functions_cpp += out_pre + values['register'] + '\n'
            
        if 'extra_info' in values:
            output_functions_cpp += values['extra_info']
            
        if 'func_name' in values:
            output_functions_cpp += out_pre + values['call_return']

            if func_called_so_return_this:
                output_functions_cpp += func_called_so_return_this
            else:
                output_functions_cpp += values['func_name'] + '(' + values['call_params'] + ')'
                
                if values['original_return_type'] == 's3eResult':
                    output_functions_cpp += ' == S3E_RESULT_SUCCESS ? true : false'
                
            output_functions_cpp += ';\n'
        
        output_functions_cpp += '}\n'

    with open(os.path.join(root_path, output_dir, output_file_prefix + '.h'), 'w') as f:
        f.write(output_api_header_h + output_functions_h + output_api_footer_h)
        
    with open(os.path.join(root_path, output_dir, output_file_prefix + '.cpp'), 'w') as f:
        f.write(output_api_header_cpp + output_functions_cpp + output_api_footer_cpp)
    
    return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Error! You must either specify the path to an extensions root folder or its .h header in order to wrap it")
    else:
        main(sys.argv[1])
