import re

participantId = "0987654321"
call = "1"
calls = "callID:" + participantId + " incoming: True address: 1111111000" + str(call) + "}"
regex = re.compile(r"\b(\w+)\s*:\s*([^:]*)(?=\s+\w+\s*:|$)")
callsExtracted = dict(regex.findall(calls))
print callsExtracted
