#!/usr/bin/env bash
# Desktop launch: keep a failed start visible, rather than flashing and closing.
cd -- "$(dirname -- "${BASH_SOURCE[0]}")" || exit 1
trap ':' INT
./run.sh "$@"
result=$?
if [[ $result -ne 0 && $result -ne 130 && -t 0 ]]; then
  printf '\nThe test could not continue. The reason is shown above.\n'
  read -r -p 'Press Enter to close this window. ' _reply
fi
exit "$result"
