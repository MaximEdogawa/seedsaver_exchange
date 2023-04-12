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
            f = tempfile.NamedTemporaryFile('w+t',suffix='_'+str(i+1)+'.pk')
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
        commandFileContent = "cat " +temp_dir.name + DEFAULT_FILE_LAUNCH
        print(commandInit)
        print(commandDerive)
        print(commandFileContent)

        try:
            proc = subprocess.Popen(commandInit, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            print(proc.stdout.read())
        except Exception as e:
            print("Error init")
            raise 

        try:
            proc = subprocess.Popen(commandDerive, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            print(proc.stdout.read())
        except Exception as e:
            print("Error derive")
            raise 

        try:
            proc = subprocess.Popen(commandFileContent, shell = True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            proc.wait()
            proc.stdin.close()
            data=proc.stdout.read()
            datahex=data.hex()
            databytes=bytes.fromhex(datahex)
            if(databytes==data):
                output = jsonify({"launch_singelton": datahex})
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

