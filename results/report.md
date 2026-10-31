# Results on 70 held-out messages


## All messages (70 messages)

| Measure | baseline (1 call) | full agent |
|---|---|---|
| Scams caught (says scam) | 97% (34/35; 95% CI 85%-99%) | 97% (34/35; 95% CI 85%-99%) |
| Scams called genuine (dangerous) | 3% (1/35; 95% CI 1%-15%) | 3% (1/35; 95% CI 1%-15%) |
| Genuine called genuine | 91% (32/35; 95% CI 78%-97%) | 89% (31/35; 95% CI 74%-95%) |
| False alarms (genuine called scam) | 6% (2/35; 95% CI 2%-19%) | 9% (3/35; 95% CI 3%-22%) |
| Genuine answered 'not sure' | 3% (1/35; 95% CI 1%-15%) | 3% (1/35; 95% CI 1%-15%) |

## Language: en (52 messages)

| Measure | baseline (1 call) | full agent |
|---|---|---|
| Scams caught (says scam) | 97% (29/30; 95% CI 83%-99%) | 97% (29/30; 95% CI 83%-99%) |
| Scams called genuine (dangerous) | 3% (1/30; 95% CI 1%-17%) | 3% (1/30; 95% CI 1%-17%) |
| Genuine called genuine | 95% (21/22; 95% CI 78%-99%) | 86% (19/22; 95% CI 67%-95%) |
| False alarms (genuine called scam) | 0% (0/22; 95% CI 0%-15%) | 9% (2/22; 95% CI 3%-28%) |
| Genuine answered 'not sure' | 5% (1/22; 95% CI 1%-22%) | 5% (1/22; 95% CI 1%-22%) |

## Language: hi (12 messages)

| Measure | baseline (1 call) | full agent |
|---|---|---|
| Scams caught (says scam) | 100% (4/4; 95% CI 51%-100%) | 100% (4/4; 95% CI 51%-100%) |
| Scams called genuine (dangerous) | 0% (0/4; 95% CI 0%-49%) | 0% (0/4; 95% CI 0%-49%) |
| Genuine called genuine | 75% (6/8; 95% CI 41%-93%) | 88% (7/8; 95% CI 53%-98%) |
| False alarms (genuine called scam) | 25% (2/8; 95% CI 7%-59%) | 12% (1/8; 95% CI 2%-47%) |
| Genuine answered 'not sure' | 0% (0/8; 95% CI 0%-32%) | 0% (0/8; 95% CI 0%-32%) |

## Language: hi-en (6 messages)

| Measure | baseline (1 call) | full agent |
|---|---|---|
| Scams caught (says scam) | 100% (1/1; 95% CI 21%-100%) | 100% (1/1; 95% CI 21%-100%) |
| Scams called genuine (dangerous) | 0% (0/1; 95% CI 0%-79%) | 0% (0/1; 95% CI 0%-79%) |
| Genuine called genuine | 100% (5/5; 95% CI 57%-100%) | 100% (5/5; 95% CI 57%-100%) |
| False alarms (genuine called scam) | 0% (0/5; 95% CI 0%-43%) | 0% (0/5; 95% CI 0%-43%) |
| Genuine answered 'not sure' | 0% (0/5; 95% CI 0%-43%) | 0% (0/5; 95% CI 0%-43%) |

## Paired comparison (same messages)

- Only **full agent** right: 1 messages ['hhi13']
- Only **baseline (1 call)** right: 2 messages ['g12', 'g13']
- Both right or both wrong: 67 messages
- Exact sign test p = 1.00 (not a significant difference)

## Invented facts in the advice (not in the message or the knowledge base)

| | baseline (1 call) | full agent |
|---|---|---|
| Scam messages: verdicts naming an invented number or website | 11% (4/35; 95% CI 5%-26%) | 0% (0/35; 95% CI 0%-10%) |
| All messages: verdicts naming an invented number or website | 7% (5/70; 95% CI 3%-16%) | 0% (0/70; 95% CI 0%-5%) |

Examples (baseline (1 call)): [('hen11', ['incometax.gov.in']), ('hen25', ['paytm.com']), ('hen53', ['incometax.gov.in']), ('hen58', ['incometax.gov.in'])]

## Cost per message

| | baseline (1 call) | full agent |
|---|---|---|
| LLM calls | 1.0 | 4.9 |
| Tokens | 1466 | 10601 |
