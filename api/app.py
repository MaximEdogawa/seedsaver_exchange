from flask import Flask, Response, jsonify, request
from .errors import errors
import subprocess
import tempfile
import codecs

CIC ="cic "
INIT ="init "
DERIVE_ROOT ="derive_root"
DEFAULT_FILE ="/'Configuration (needs derivation).txt'"
DEFAULT_FILE_LAUNCH ="/'Configuration (awaiting launch).txt'"
LAUNCH_SIGNELTON = "launch_singleton "
PAYMENT = "payment "
PUSH_TX = "push_tx "
DEFAULT_FEE = 10000000
COMPLETE = "complete "
COMPLETE_FILE = "complete.signed"
CLAWBACK = "clawback "

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

        # Create temp file list
        files = []
        pub_fileNameList=""
        for i in range(len(pubkeys_strings)):
            f = tempfile.NamedTemporaryFile('w+t',suffix=str(i+1)+'.pk', dir=temp_dir.name)
            f.write(pubkeys_strings[i])
            f.seek(0)
            files.append(f)
            if((i+1)<len(pubkeys_strings)):
                pub_fileNameList+=(f.name)+","
            else:
                pub_fileNameList+=(f.name)

        current_lock_level = payload.get("current_lock_level")
        maximum_lock_level = payload.get("maximum_lock_level")
       
        commandInit = CIC + INIT + " -d " + temp_dir.name + " -wt " + withdraw_timelock + " -pc " + payment_clawback + " -rt " + rekey_timelock + " -rc " + rekey_clawback + " -sp " + slow_rekey_penalty
        commandDerive = CIC + DERIVE_ROOT + " -c " + temp_dir.name + DEFAULT_FILE + " -pks " + "'" + pub_fileNameList + "'" + " -m " + current_lock_level + " -n " + maximum_lock_level
        commandLaunchSigelon = CIC + LAUNCH_SIGNELTON + " -c " + temp_dir.name + DEFAULT_FILE_LAUNCH +" --fee " + DEFAULT_FEE

        print(commandInit)
        print(commandDerive)
        print(commandLaunchSigelon)

        try:
            proc = subprocess.Popen(commandInit, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error init")
            raise 

        try:
            proc = subprocess.Popen(commandDerive, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error derive")
            raise 

        try:
            proc = subprocess.Popen(commandLaunchSigelon, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error launch")
            raise

        commandGetFileName = "ls " + temp_dir.name
        print(commandGetFileName)
        try:
            proc = subprocess.Popen(commandGetFileName, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            launched_fileName = "/'" + proc.stdout.read().decode("utf-8") + "'"
        except Exception as e:
            print("Error launch")
            raise

        commandFileContent = "cat " + temp_dir.name + launched_fileName
        print(commandFileContent)
        try:
            proc = subprocess.Popen(commandFileContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            data=proc.stdout.read()
            datahex=data.hex()
            databytes=bytes.fromhex(datahex)
            if(databytes==data):
                output = jsonify({"launched_singelton": datahex})
            else:
                output = "..."
        except Exception as e:
            output = "..."
            print("Error launch")
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
        data=payload.get("launched_singelton")
        temp_dir = tempfile.TemporaryDirectory()
        temp_file = tempfile.NamedTemporaryFile('w+t',suffix='.txt', dir=temp_dir.name)
        temp_file.write(data)
        temp_file.seek(0)

        commandStatus = CIC + "sync -c " + temp_dir.name + "/" + temp_file.name +" -s "
        print(commandStatus)
        try:
            proc = subprocess.Popen(commandStatus, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            output=proc.stdout.read()
        except Exception as e:
            print("Error launch")
            raise
        output = jsonify({"message": data })
    else:
        output = jsonify({"message": "..."})

    temp_file.close()
    temp_dir.cleanup()
    return output

@app.route("/withdrawal", methods=["POST"])
def withdrawal():
    payload = request.get_json()

    if payload.get("withdrawal_create") is True:
        temp_dir = tempfile.TemporaryDirectory()
        temp_file = "/withdrawal.unsigned"
        pubkeys_strings = payload.get("pubkeys_strings")
        withdraw_mojos = payload.get("withdraw_mojos")
        recipient_address = payload.get("recipient address") 

        # Create temp file list
        files = []
        pub_fileNameList=""
        for i in range(len(pubkeys_strings)):
            f = tempfile.NamedTemporaryFile('w+t',suffix=str(i+1)+'.pk', dir=temp_dir.name)
            f.write(pubkeys_strings[i])
            f.seek(0)
            files.append(f)
            if((i+1)<len(pubkeys_strings)):
                pub_fileNameList+=(f.name)+","
            else:
                pub_fileNameList+=(f.name)

        commandWithdraw = CIC + PAYMENT + " -f " + temp_dir + temp_file + " -pks " + pub_fileNameList + " -a " + withdraw_mojos + " -t " + recipient_address +" -ap "
        print(commandWithdraw)
        try:
            proc = subprocess.Popen(commandWithdraw, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error launch")
            raise

        commandFileContent = "cat " + temp_dir.name + temp_file
        print(commandFileContent)
        try:
            proc = subprocess.Popen(commandFileContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            data=proc.stdout.read()
            datahex=data.hex()
            databytes=bytes.fromhex(datahex)
            if(databytes==data):
                output = jsonify({"withdrawal_unsigned": datahex})
            else:
                output = "..."
        except Exception as e:
            output = "..."
            print("Error withdrawal unsigned")
            raise
        list(map(lambda f: f.close(), files))
        f.close()
        temp_dir.cleanup()
    elif payload.get("withdrawal_push") is True:
        temp_dir = tempfile.TemporaryDirectory()
        withdrawal_signed = payload.get("withdrawal_signed")
        file = tempfile.NamedTemporaryFile('w+t',suffix='.signed', dir=temp_dir.name)
        file.write(withdrawal_signed)
        file.seek(0)

        commandWithdrawPush = CIC + PUSH_TX + " -b " + temp_dir.name +"/"+file.name + " -m " + DEFAULT_FEE
        print(commandWithdrawPush)
        try:
            proc = subprocess.Popen(commandWithdrawPush, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error withdrawal push")
            raise

        file.close()
        temp_dir.cleanup()
    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/complete", methods=["POST"])
def complete():
    payload = request.get_json()

    if payload.get("complete") is True:
       temp_dir = tempfile.TemporaryDirectory()
       withdrawal_signed = payload.get("withdrawal_signed")
       tempFile = tempfile.NamedTemporaryFile('w+t',suffix='.signed', dir=temp_dir.name)
       tempFile.write(withdrawal_signed)
       tempFile.seek(0)
       commandComplete = "cd " +  temp_dir.name + " && " + CIC + COMPLETE + " -f " + COMPLETE_FILE
       print(commandComplete)
       try:
            proc = subprocess.Popen(commandComplete, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
       except Exception as e:
            print ("Error complete create")
            raise

       commandCompletePush = CIC + PUSH_TX + " -b " + temp_dir.name + "/" + tempFile.name + " -m " + DEFAULT_FEE
       print(commandCompletePush)
       try:
            proc = subprocess.Popen(commandComplete, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
       except Exception as e:
            print ("Error complete create")
            raise
       tempFile.close()
       temp_dir.cleanup()
    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/clawback", methods=["POST"])
def custom():
    payload = request.get_json()
    
    if payload.get("clawback_create") is True:
        clawback_unsigned=payload.get("clawback_unsigned")
        pubkeys_strings = payload.get("pubkeys_strings")

        temp_dir = tempfile.TemporaryDirectory()
        tempFile = tempfile.NamedTemporaryFile('w+t',suffix='.unsigned', dir=temp_dir.name)
        tempFile.write(clawback_unsigned)
        tempFile.seek(0)

        # Create temp file list
        files = []
        pub_fileNameList=""
        for i in range(len(pubkeys_strings)):
            f = tempfile.NamedTemporaryFile('w+t',suffix=str(i+1)+'.pk', dir=temp_dir.name)
            f.write(pubkeys_strings[i])
            f.seek(0)
            files.append(f)
            if((i+1)<len(pubkeys_strings)):
                pub_fileNameList+=(f.name)+","
            else:
                pub_fileNameList+=(f.name)

        commandClawback = CIC + CLAWBACK + " -f " + temp_dir +"/"+tempFile.name +" -pks " + pub_fileNameList
        try:
            proc = subprocess.Popen(commandClawback, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print ("Error clawback create")
            raise

        list(map(lambda f: f.close(), files))
        tempFile.close()
        temp_dir.cleanup()  

    elif payload.get("clawback_push") is True:
        temp_dir = tempfile.TemporaryDirectory()
        clawback_signed = payload.get("clawback_signed")
        file = tempfile.NamedTemporaryFile('w+t',suffix='.signed', dir=temp_dir.name)
        file.write(clawback_signed)
        file.seek(0)

        commandClawbackPush = CIC + PUSH_TX + " -b " + temp_dir.name + "/" + file.name + " -m " + DEFAULT_FEE
        print(commandClawbackPush)
        try:
            proc = subprocess.Popen(commandClawbackPush, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
        except Exception as e:
            print("Error clawback push")
            raise

        file.close()
        temp_dir.cleanup()    
    else:
        output = jsonify({"message": "..."})

    return output

@app.route("/spendbundle", methods=["POST"])
def custom():
    payload = request.get_json()

    if payload.get("generate_spendbundle") is True:
        data=payload.get("pubkeys_strings")
        output = jsonify({"message": data[0] })
    else:
        output = jsonify({"message": "..."})

    return output


@app.route("/health")
def health():
    return Response("OK", status=200)

