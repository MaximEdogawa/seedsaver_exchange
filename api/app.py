from flask import Flask, Response, jsonify, request
from .errors import errors 
import subprocess
import tempfile
import os
import re
import logging
CIC ="cic "
INIT ="init "
DERIVE_ROOT ="derive_root"
DEFAULT_FILE ="/'Configuration (needs derivation).txt'"
DEFAULT_FILE_LAUNCH ="/'Configuration (awaiting launch).txt'"
LAUNCH_SIGNELTON = "launch_singleton "
PAYMENT = "payment "
PUSH_TX = "push_tx "
DEFAULT_FEE = "50000"
COMPLETE = "complete "
COMPLETE_FILE = "complete.signed"
CLAWBACK = "clawback "
START_REKEY = "start_rekey "
INCREASE_SECURITTY_LEVEL =" increase_security_level "

app = Flask(__name__)
app.register_blueprint(errors)
@app.route("/")

def index():
    return Response("Hello, world!", status=200)

@app.route("/init", methods=["POST"])
def init():
    payload = request.get_json()
    if payload.get("init_singelton") is True:
        temp_dir = tempfile.TemporaryDirectory()
        withdraw_timelock=payload.get("withdraw_timelock")
        payment_clawback=payload.get("payment_clawback")
        rekey_timelock=payload.get("rekey_timelock")
        rekey_clawback=payload.get("rekey_clawback")
        slow_rekey_penalty=payload.get("slow_rekey_penalty")
        pubkeys_strings= payload.get("pubkeys_strings")
        current_lock_level = payload.get("current_lock_level")
        maximum_lock_level = payload.get("maximum_lock_level")
        
        print(withdraw_timelock)
        print(payment_clawback)
        print(rekey_timelock)
        print(rekey_clawback)
        print(slow_rekey_penalty)
        print(pubkeys_strings)
        print(current_lock_level)
        print(maximum_lock_level)

        files = []
        pub_fileNameList=""
        for i in range(len(pubkeys_strings)):
            with open(os.path.join(temp_dir.name, str(i+1)+'.pk'), 'w') as f:
                print("Create files:"+str(i+1))
                f.write(pubkeys_strings[i])
                f.seek(0)
                files.append(f)
                if((i+1)<len(pubkeys_strings)):
                    pub_fileNameList+=f.name + ","
                else:
                    print("last")
                    pub_fileNameList+=f.name
                pass
        print("commands")
        commandInit = CIC + INIT + " -d " + temp_dir.name + " -wt " + withdraw_timelock + " -pc " + payment_clawback + " -rt " + rekey_timelock + " -rc " + rekey_clawback + " -sp " + slow_rekey_penalty
        print(commandInit)

        commandDerive = CIC + DERIVE_ROOT + " -c " + temp_dir.name + DEFAULT_FILE + " -pks " + "'" + pub_fileNameList + "'" + " -m " + current_lock_level + " -n " + maximum_lock_level
        print(commandDerive)

        commandLaunchSingelton = CIC + LAUNCH_SIGNELTON + " -c " + temp_dir.name + DEFAULT_FILE_LAUNCH +" --fee " + DEFAULT_FEE
        print(commandLaunchSingelton)

        try:
            proc = subprocess.Popen(commandInit, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            print("Success init")
        except Exception as e:
            print("Error init")
            raise 
        try:
            proc = subprocess.Popen(commandDerive, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            print("Success derive")
        except Exception as e:
            print("Error derive")
            raise 
        try:
            proc = subprocess.Popen(commandLaunchSingelton, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            print("Success launch")
        except Exception as e:
            print("Error launch")
            raise

        commandGetFileName = "cd "+ temp_dir.name +" && "+ "ls " "*.txt"
        print(commandGetFileName)
        try:
            proc = subprocess.Popen(commandGetFileName, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            launched_fileName_full =  proc.stdout.read().decode("utf-8")
            print("Success Get File Name")
        except Exception as e:
            print("Error Get File Name")
            raise
        
        result = extract_string_between_parentheses(launched_fileName_full)

        commandFileContent = "cat " + temp_dir.name + "/'Configuration ("+result+").txt'" 
        try:
            proc = subprocess.Popen(commandFileContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            data=proc.stdout.read()
            datahex=data.hex()
            databytes=bytes.fromhex(datahex)
            if(databytes==data):
                output = jsonify({"Success": "true","launched_singelton_hex": datahex, "id": result})
            else:
                output = jsonify({"Success": "false"})
            print("Success Get File Content")
        except Exception as e:
            output = "..."
            print("Error Get File Content")
            raise

        list(map(lambda f: f.close(), files))
        temp_dir.cleanup()
    else:
        output = jsonify({"message": "..."})
    
    return output

@app.route("/status", methods=["POST"])
def status():
    payload = request.get_json()

    if payload.get("sync") is True:
        data=payload.get("launched_singelton_hex")
        id=payload.get("id")
        temp_dir = tempfile.TemporaryDirectory()
        bytes_data = bytes.fromhex(data)

        with open(os.path.join(temp_dir.name, id+'.txt'), 'wb') as f:
            f.write(bytes_data)
            f.seek(0)
            pass
        
        commandStatus = CIC + "sync -c "+ f.name +" -db " + temp_dir.name
        try:
            proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error status")
            raise

        commandStatusShow= "cd "+ temp_dir.name+" && cic sync -s" 
        try:
            proc = subprocess.Popen(commandStatusShow, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            status = proc.stdout.read().decode("utf-8")
            status = status.replace('\n', ' ')
            output=jsonify({"launched_singelton_info": status})
        except Exception as e:
            print("Error status show")
            raise
        
        temp_dir.cleanup()

    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/get_address", methods=["POST"])
def get_address():
    payload = request.get_json()

    if payload.get("address") is True:
        data=payload.get("launched_singelton_hex")
        id=payload.get("id")
        bytes_data = bytes.fromhex(data)
        temp_dir = tempfile.TemporaryDirectory()

        with open(os.path.join(temp_dir.name, id+'.txt'), 'wb') as f:
            f.write(bytes_data)
            f.seek(0)
            pass
        
        commandStatus = CIC + "sync -c "+ f.name +" -db " + temp_dir.name
        try:
            proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error status")
            raise

        commandStatusShow= "cd "+ temp_dir.name +" && cic p2_address --prefix txch" 
        try:
            proc = subprocess.Popen(commandStatusShow, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            address=proc.stdout.read().decode("utf-8")
            address=address.replace('\n', '')
            output=jsonify({"vault_address": address })
        except Exception as e:
            print("Error get address")
            raise
        
        temp_dir.cleanup()
    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/withdrawal", methods=["POST"])
def withdrawal():
    payload = request.get_json()

    if payload.get("withdrawal_create") is True:
        data=payload.get("launched_singelton_hex")
        id=payload.get("id")
        bytes_data = bytes.fromhex(data)
        temp_dir = tempfile.TemporaryDirectory()
        pubkeys_strings = payload.get("pubkeys_strings")
        withdraw_mojos = payload.get("withdraw_mojos")
        recipient_address = payload.get("recipient address") 

        with open(os.path.join(temp_dir.name, id+'.txt'), 'wb') as temp_file:
            temp_file.write(bytes_data)
            temp_file.seek(0)
            pass
        
        commandStatus = CIC + "sync -c "+ temp_file.name +" -db " + temp_dir.name
        try:
            proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error status")
            raise

        files = []
        pub_fileNameList=""
        for i in range(len(pubkeys_strings)):
            with open(os.path.join(temp_dir.name, str(i+1)+'.pk'), 'w') as f:
                print("Create files:"+str(i+1))
                f.write(pubkeys_strings[i])
                f.seek(0)
                files.append(f)
                if((i+1)<len(pubkeys_strings)):
                    pub_fileNameList+=f.name + ","
                else:
                    pub_fileNameList+=f.name
                pass

        commandWithdraw = CIC + PAYMENT + "-db " + temp_dir.name + " -f "+ temp_dir.name +"/withdrawal.unsigned" + " -pks " + "'" + pub_fileNameList + "'" + " -a " + withdraw_mojos + " -t " + recipient_address +" -ap"
        print(commandWithdraw)
        try:
            proc = subprocess.Popen(commandWithdraw, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error launch")
            raise

        commandFileContent = "cat " + temp_dir.name + "/withdrawal.unsigned"
        print(commandFileContent)
        try:
            proc = subprocess.Popen(commandFileContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            data=proc.stdout.read().decode("utf-8")
            output = jsonify({"withdrawal_unsigned": data})
        except Exception as e:
            output = "..."
            print("Error withdrawal unsigned")
            raise
        list(map(lambda f: f.close(), files))
        f.close()
        temp_dir.cleanup()
    elif payload.get("withdrawal_push") is True:
        temp_dir = tempfile.TemporaryDirectory()
        data = payload.get("withdrawal_signed")
        bytes_data = bytes.fromhex(data)

        with open(os.path.join(temp_dir.name, 'withdrawal.signed'), 'wb') as f:
            f.write(bytes_data)
            f.seek(0)
            pass

        commandWithdrawPush = CIC + PUSH_TX + "-b " + f.name + " -m " + DEFAULT_FEE
        try:
            proc = subprocess.Popen(commandWithdrawPush, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            output = jsonify({"message": "Successfull withdrawal_push"})
        except Exception as e:
            print("Error withdrawal push")
            output = jsonify({"message": "..."})
            raise
        temp_dir.cleanup()
    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/complete", methods=["POST"])
def complete():
    payload = request.get_json()

    if payload.get("complete") is True:
       payment_index= payload.get("payment_index")
       temp_dir = tempfile.TemporaryDirectory()
       data=payload.get("launched_singelton_hex")
       id=payload.get("id")
       bytes_data = bytes.fromhex(data)
       
       with open(os.path.join(temp_dir.name, id+'.txt'), 'wb') as f:
            f.write(bytes_data)
            f.seek(0)
            pass
       
       commandStatus = CIC + "sync -c "+ f.name +" -db " + temp_dir.name
       try:
            proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
       except:
           print("Error sync")
           raise
       
       commandSync = "cd "+ temp_dir.name + " && "+ CIC + "sync -s "
       try:
            proc = subprocess.Popen(commandSync, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
       except:
           print("Error sync")
           raise
    
       commandComplete = "cd "+ temp_dir.name + " && "+ CIC + COMPLETE + " -f "+ temp_dir.name +"/complete.signed"
       try:
            proc = subprocess.Popen(commandComplete, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            input_bytes = payment_index.encode('utf-8') + b'\n'
            proc.stdin.write(input_bytes)
            proc.stdin.close()
            output = proc.stdout.read().decode('utf-8')
            print(output)
       except Exception as e:
            print("Error complete create")
            raise
       
       commandFileContent = "cat " + temp_dir.name + "/complete.signed"
       try:
           proc = subprocess.Popen(commandFileContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
           proc.wait()
           proc.stdin.close()
           data=proc.stdout.read().decode("utf-8")
           print(data)
       except Exception as e:
           print("Error get Complete")
           raise

       commandCompletePush = CIC + PUSH_TX + "-b "+ temp_dir.name +"/complete.signed" + " -m " + DEFAULT_FEE
       try:
            proc = subprocess.Popen(commandCompletePush, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            output = proc.stdout.read().decode('utf-8')
       except Exception as e:
            print("Error complete create")
            output = jsonify({"message": "..."})
            raise
       temp_dir.cleanup()
    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/clawback", methods=["POST"])
def clawback():
    payload = request.get_json()
    
    if payload.get("clawback_create") is True:
        temp_dir = tempfile.TemporaryDirectory()
        data=payload.get("launched_singelton_hex")
        id=payload.get("id")
        pubkeys_strings = payload.get("pubkeys_strings")
        payment_index= payload.get("payment_index")
        bytes_data = bytes.fromhex(data)

        with open(os.path.join(temp_dir.name, id + '.txt'), 'wb') as configure_file:
                configure_file.write(bytes_data)
                configure_file.seek(0)
                pass
        
        files = []
        pub_fileNameList=""
        for i in range(len(pubkeys_strings)):
            with open(os.path.join(temp_dir.name, str(i+1)+'.pk'), 'w') as f:
                print("Create files:"+str(i+1))
                f.write(pubkeys_strings[i])
                f.seek(0)
                files.append(f)
                if((i+1)<len(pubkeys_strings)):
                    pub_fileNameList+=f.name + ","
                else:
                    pub_fileNameList+=f.name
                pass

        commandStatus = CIC + "sync -c "+ configure_file.name +" -db " + temp_dir.name 
        try:
                proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                proc.wait()
                proc.stdin.close()
                print("Success sync create")
        except:
            print("Error sync")
            raise
        
        commandSync = "cd "+ temp_dir.name + " && "+ CIC + "sync -s "
        try:
            proc = subprocess.Popen(commandSync, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            print("Success sync")
        except:
            print("Error sync")
            raise

        commandClawback = "cd "+ temp_dir.name +" && "+ CIC + CLAWBACK + " -f " + temp_dir.name +"/clawback.unsigned -pks " + pub_fileNameList
        try:
            proc = subprocess.Popen(commandClawback, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            input_bytes = payment_index.encode('utf-8') + b'\n'
            proc.stdin.write(input_bytes)
            proc.stdin.close()
            output = proc.stdout.read().decode('utf-8')
        except Exception as e:
            print("Error clawback create")
            raise

        if output == "No actions outstanding\n": 
            output = jsonify({"clawback_unsigned": output})
        else:
            commandFileContent = "cat " + temp_dir.name + "/clawback.unsigned"
            print(commandFileContent)
            proc = subprocess.Popen(commandFileContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            data=proc.stdout.read().decode("utf-8")
            output = jsonify({"clawback_unsigned": data})     

        list(map(lambda f: f.close(), files))
        temp_dir.cleanup()  

    elif payload.get("clawback_push") is True:
        temp_dir = tempfile.TemporaryDirectory()
        clawback_signed = payload.get("clawback_signed")
        payment_index= payload.get("payment_index")
        bytes_data = bytes.fromhex(clawback_signed)

        with open(os.path.join(temp_dir.name, 'clawback.signed'), 'wb') as f:
            f.write(bytes_data)
            f.seek(0)
            pass

        commandClawbackPush = CIC + PUSH_TX + "-b " + f.name + " -m " + DEFAULT_FEE
        try:
            proc = subprocess.Popen(commandClawbackPush, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            input_bytes = payment_index.encode('utf-8') + b'\n'
            proc.stdin.write(input_bytes)
            proc.stdin.close()
            output = jsonify({"message": proc.stdout.read().decode('utf-8')})
        except Exception as e:
            print("Error clawback push")
            raise

        temp_dir.cleanup()    
    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/rekey", methods=["POST"])
def rekey():
    payload = request.get_json()

    if payload.get("rekey_create") is True:
        data=payload.get("launched_singelton_hex")
        id=payload.get("id")
        bytes_data = bytes.fromhex(data)
        temp_dir = tempfile.TemporaryDirectory()
        new_pubkeys_strings = payload.get("new_pubkeys_strings")
        pubkeys_strings = payload.get("pubkeys_strings")
        current_lock_level = payload.get("current_lock_level")
        maximum_lock_level = payload.get("maximum_lock_level")

        with open(os.path.join(temp_dir.name, id+'.txt'), 'wb') as temp_file:
            temp_file.write(bytes_data)
            temp_file.seek(0)
            pass
        
        commandStatus = CIC + "sync -c "+ temp_file.name +" -db " + temp_dir.name
        try:
            proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error status")
            raise

        files = []
        pub_fileNameList=""
        for i in range(len(pubkeys_strings)):
            with open(os.path.join(temp_dir.name, str(i+1)+'.pk'), 'w') as f: 
                f.write(pubkeys_strings[i])
                f.seek(0)
                files.append(f)
                if((i+1)<len(pubkeys_strings)):
                    pub_fileNameList+=f.name + ","
                else:
                    pub_fileNameList+=f.name
                pass\
                
        new_files = []
        new_pub_fileNameList=""
        for i in range(len(new_pubkeys_strings)):
            with open(os.path.join(temp_dir.name, str(i+1)+'_new.pk'), 'w') as new_f:
                new_f.write(new_pubkeys_strings[i])
                new_f.seek(0)
                new_files.append(f)
                if((i+1)<len(new_pubkeys_strings)):
                    new_pub_fileNameList+=new_f.name + ","
                else:
                    new_pub_fileNameList+=new_f.name
                pass

        commandDeriveRoot = "cd "+temp_dir.name+" && "+CIC + DERIVE_ROOT + " -db  " + temp_dir.name +"/'sync ("+id+").sqlite'"+ " -c "+temp_dir.name+"/'Configuration (after rekey).txt'" + " -pks " + "'" + new_pub_fileNameList + "'" + " -m "+current_lock_level+ " -n "+ maximum_lock_level
        try:
            proc = subprocess.Popen(commandDeriveRoot, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error Derive Root rekey")
            raise

        commandStartRekey ="cd "+temp_dir.name+" && "+ CIC + START_REKEY +" -f "+ temp_dir.name +"/rekey.unsigned" + " -pks " + "'" + pub_fileNameList + "'" +" -new "+temp_dir.name+"/'Configuration (after rekey).txt'"  
        try:
            proc = subprocess.Popen(commandStartRekey, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            print(proc.stdout.read().decode("utf-8"))
        except Exception as e:
            output = "..."
            print("Error rekey unsigned")
            raise

        commandGetRekeyContent = "cat " + temp_dir.name + "/rekey.unsigned"
        try:
            proc = subprocess.Popen(commandGetRekeyContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            rekey_data=proc.stdout.read().decode("utf-8")
        except Exception as e:
            rekey_data = "..."
            print("Error withdrawal unsigned")
            raise

        commandGetNewConfigContent = "cat " + temp_dir.name + "/'Configuration (after rekey).txt'"
        try:
            proc = subprocess.Popen( commandGetNewConfigContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            config_data=proc.stdout.read()
            config_data_hex=config_data.hex()
        except Exception as e:
            config_data = "..."
            print("Error rekey unsigned")
            raise

        output=jsonify({"rekey_unsigned": rekey_data, "rekey_singelton_hex": config_data_hex})
        list(map(lambda f: f.close(), files))
        f.close()
        list(map(lambda new_f: new_f.close(), new_files))
        new_f.close()
        temp_dir.cleanup()
    elif payload.get("rekey_push") is True:
        temp_dir = tempfile.TemporaryDirectory()
        data = payload.get("rekey_signed")
        bytes_data = bytes.fromhex(data)

        with open(os.path.join(temp_dir.name, 'rekey.signed'), 'wb') as f:
            f.write(bytes_data)
            f.seek(0)
            pass

        commandRekeyPush = CIC + PUSH_TX + "-b " + f.name + " -m " + DEFAULT_FEE
        try:
            proc = subprocess.Popen(commandRekeyPush, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            data=proc.stdout.read().decode("utf-8")
            output = jsonify({"message":  data})
        except Exception as e:
            print("Error rekey push")
            output = jsonify({"message": "..."})
            raise
        temp_dir.cleanup()
    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/update", methods=["POST"])
def update():
    payload = request.get_json()

    if payload.get("update_config") is True:
        data=payload.get("launched_singelton_hex")
        bytes_data = bytes.fromhex(data)
        temp_dir = tempfile.TemporaryDirectory()

        with open(os.path.join(temp_dir.name,'Configuration (after rekey).txt'), 'wb') as f_config:
            f_config.write(bytes_data)
            f_config.seek(0)
            pass

        commandStatus = CIC + "sync -c "+temp_dir.name+"/'Configuration (after rekey).txt' -db " + temp_dir.name
        try:
            proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except:
           print("Error sync")
           raise

        commandShow = "cd "+temp_dir.name+" && "+CIC + " show -d"
        try:
            proc = subprocess.Popen(commandShow, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error show")
            raise

        commandUpdate ="cd "+temp_dir.name+" && "+"cic update_config -c './Configuration (after rekey).txt'"
        try:
            proc = subprocess.Popen(commandUpdate, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error update")
            raise

        commandShow = "cd "+temp_dir.name+" && "+CIC + " show -d"
        try:
            proc = subprocess.Popen(commandShow, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            data=proc.stdout.read().decode("utf-8")
            output = jsonify({"message": data})
        except Exception as e:
            print("Error show")
            output = jsonify({"message": "..."})
            raise

    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/locklevel", methods=["POST"])
def locklevel():
    payload = request.get_json()

    if payload.get("locklevel_increase") is True:
        data=payload.get("launched_singelton_hex")
        id=payload.get("id")
        bytes_data = bytes.fromhex(data)
        temp_dir = tempfile.TemporaryDirectory()
        new_pubkeys_strings = payload.get("new_pubkeys_strings")

        with open(os.path.join(temp_dir.name,'Configuration (after rekey).txt'), 'wb') as f_config:
            f_config.write(bytes_data)
            f_config.seek(0)
            pass
                
        new_files = []
        new_pub_fileNameList=""
        for i in range(len(new_pubkeys_strings)):
            with open(os.path.join(temp_dir.name, str(i+1)+'_new.pk'), 'w') as f_new:
                f_new.write(new_pubkeys_strings[i])
                f_new.seek(0)
                new_files.append(f_new)
                if((i+1)<len(new_pubkeys_strings)):
                    new_pub_fileNameList+=f_new.name + ","
                else:
                    new_pub_fileNameList+=f_new.name
                pass

        commandStatus = CIC + "sync -c "+temp_dir.name+"/'Configuration (after rekey).txt' -db " + temp_dir.name
        try:
            proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except:
           print("Error sync")
           raise

        commandShow = "cd "+temp_dir.name+" && "+CIC + " show -d"
        try:
            proc = subprocess.Popen(commandShow, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error show")
            raise

        commandUpdate ="cd "+temp_dir.name+" && "+"cic update_config -c './Configuration (after rekey).txt'"
        try:
            proc = subprocess.Popen(commandUpdate, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error update")
            raise

        commandShow = "cd "+temp_dir.name+" && "+ CIC + " show -d"
        try:
            proc = subprocess.Popen(commandShow, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error show")
            output = jsonify({"message": "..."})
            raise

        commandIncreaseLockLevel = "cd "+temp_dir.name+" && "+CIC + INCREASE_SECURITTY_LEVEL + " -db  " + temp_dir.name +"/'sync ("+id+").sqlite'" +  " -pks " + "'" + new_pub_fileNameList + "'" + " -f "+temp_dir.name+"/lock.unsigned"
        try:
            proc = subprocess.Popen(commandIncreaseLockLevel, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            data=proc.stdout.read().decode("utf-8")
            print(data)
        except Exception as e:
            print("Error Increase Lock Level")
            raise

        commandFileContent = "cat " + temp_dir.name + "/lock.unsigned"
        try:
            proc = subprocess.Popen(commandFileContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            data=proc.stdout.read().decode("utf-8")
            output = jsonify({"lock_unsigned": data})
        except Exception as e:
            output = "..."
            print("Error lock unsigned")
            raise
        list(map(lambda f_new: f_new.close(), new_files))
        new_files.close()
        temp_dir.cleanup()  
    else:
        output = jsonify({"message": "..."})

    return output

def extract_string_between_parentheses(string):
    match = re.search(r'\((.*?)\)', string)
    if match:
        return match.group(1)
    else:
        return None

