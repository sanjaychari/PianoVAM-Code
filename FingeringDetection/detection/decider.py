"""
Fingering decision logic: keyhandlist → fingerinfo conversion
"""
from .midicomparison import pitch_list
from .fingergt import jeuxdeau_150


def decide_fingering(tokenlist, keyhandlist):
    """
    Decide final fingering per note based on keyhandlist (per-frame key-hand matching).
    
    Returns:
        pressedfingerlist: Finger number (1~10) per note or "Noinfo"
        undecidedtokeninfolist: List of notes requiring manual review
    """
    pressedfingerlist = [None] * len(tokenlist)
    undecidedtokeninfolist = []

    for i in range(len(tokenlist)):
        totalframe = tokenlist[i][2] - tokenlist[i][0]
        tokenlist[i].pop(2)
        tokenlist[i][1] = pitch_list[tokenlist[i][1]]

        lefthandcounter = 0
        righthandcounter = 0
        noinfocounter = 0
        fingerscore = [0] * 10
        fingerindex = [[], [], [], [], [], [], [], [], [], [], 0]

        for j in range(len(keyhandlist)):
            framekeyhandinfo = keyhandlist[j]
            for keyhandinfo in framekeyhandinfo:
                if keyhandinfo[1] != i:
                    continue
                if keyhandinfo[2] == "Left":
                    lefthandcounter += 1
                    for k in range(1, 11):
                        if keyhandinfo[3][k] != 0:
                            fingerindex[k - 1].append(j)
                            fingerscore[k - 1] += keyhandinfo[3][k]
                    if keyhandinfo[3] == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]:
                        fingerindex[10] += 1
                elif keyhandinfo[2] == "Right":
                    righthandcounter += 1
                    for k in range(1, 11):
                        if keyhandinfo[3][k] != 0:
                            fingerindex[k - 1].append(j)
                            fingerscore[k - 1] += keyhandinfo[3][k]
                    if keyhandinfo[3] == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]:
                        fingerindex[10] += 1
                elif keyhandinfo[2] == "Noinfo":
                    noinfocounter += 1
                    fingerindex[10] += 1

        counterlist = [
            lefthandcounter,
            righthandcounter,
            noinfocounter,
            (lefthandcounter + righthandcounter + noinfocounter) / 2,
        ]
        if counterlist.index(max(counterlist)) == 0:
            tokenlist[i].append("Left")
        elif counterlist.index(max(counterlist)) == 1:
            tokenlist[i].append("Right")
        else:
            tokenlist[i].append("Noinfo")

        pressedfingers = []
        highcandidates = []
        totalfingercount = 0
        c = 0
        for j in range(10):
            if fingerscore[j] != 0:
                pressedfingers.append([j + 1, fingerscore[j]])
                totalfingercount += fingerscore[j]

        while c < len(pressedfingers):
            finger = pressedfingers[c]
            if finger[1] / totalframe < 0.5:
                pressedfingers.pop(c)
                c -= 1
            elif finger[1] / totalframe > 0.80:
                highcandidates.append(finger)
            c += 1

        gt = jeuxdeau_150
        if c > 1:
            if len(highcandidates) == 1:
                pressedfingerlist[i] = highcandidates[0][0]
            else:
                undecidedtokeninfolist.append([i, tokenlist[i], pressedfingers, totalframe])
        elif c == 1:
            pressedfingerlist[i] = pressedfingers[0][0]
        elif c == 0:
            pressedfingerlist[i] = "Noinfo"
            undecidedtokeninfolist.append([i, tokenlist[i], [], totalframe])

    return pressedfingerlist, undecidedtokeninfolist
