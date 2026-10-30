#!/bin/zsh
cd /Users/kennygeiler/ai-capex-ledger
export LEDGER_CLAUDE="${LEDGER_CLAUDE:-$CLAUDE_CODE_EXECPATH}"
B=(
"NBIS HUT RIOT MARA CLSK BTBT SLNH GLXY BTDR"
"ARM MPWR RMBS SITM SNPS CDNS LRCX AMAT KLAC TER ENTG ONTO AEIS ACLS"
"WDC STX SNDK SMCI DELL HPE NTAP CIEN COHR LITE AAOI FN JBL FLEX CLS PENG"
"VRT ETN NVT MOD JCI PWR FIX EME GEV POWL BE EQIX DLR IRM"
"VST CEG NRG TLN CRM NOW ADBE SNOW PLTR DDOG UBER SYM VZ T TMUS FCX"
)
for b in $B; do
  echo "##### batch: $b  $(date -u +%FT%TZ)"
  uv run python -m ledger run --ticker ${=b}
  echo "##### batch exit $?  $(date -u +%FT%TZ)"
done
echo "##### ALL DONE $(date -u +%FT%TZ)"
