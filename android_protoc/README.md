# Android Proto
This directory contains compiled proto files from Android frameworks.

To update the list of checked in proto files, add the module you want to
PROTO_MODULES in codegen/gen.py and then run it. You will need git and protoc in
your environment.

To use generated protos, import directly from android_proto, e.g.:
```
from android_protoc import activitymanagerservice_pb2
```
