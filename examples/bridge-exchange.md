# Worked example: one Bridge exchange, end to end

A server needs a chat created on the chat platform it bridges to. The payload (the standing brief for the new chat) is already written to the bridge queue as a file; the chat message is only the frame.

Server posts into the Bridge chat:

```
§CANT/1 REQ 9f3ac21e
op=CRT
name=🧪 bridge throwaway P2
arg=@file:/example/bridge-queue/9f3ac21e.json
§/CANT 9f3ac21e
```

The Bridge worker reads the referenced file, creates the chat with its chat tools, seeds the brief, writes the result file, and answers with one frame and nothing else:

```
§CANT/1 RES 9f3ac21e
st=ok
chat=00000000-0000-0000-0000-000000000000
ms=41200
out=@file:/example/bridge-results/9f3ac21e.json
§/CANT 9f3ac21e
```

A failure looks like this (the named chat does not exist):

```
§CANT/1 ERR 51bd07aa
err=notfound
op=RED
chat=00000000-0000-0000-0000-000000000000
ms=3100
§/CANT 51bd07aa
```

And a malformed frame is answered in English, outside the frame system entirely, e.g.: "Cant parse failure on the frame beginning §CANT/1 REQ 77aa — close token corr mismatch. No action taken." That is deliberate: parse failures are operator-visible events, not machine traffic.
