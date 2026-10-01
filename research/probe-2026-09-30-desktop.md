# Probe — desktop, 2026-09-30 23:46 UTC

A source passes on a client when every step of its sequence passes.

| Source | Passes with |
| --- | --- |
| apple_refurb | requests, curl_cffi |
| apple_new | requests, curl_cffi |
| orchard | requests, curl_cffi |
| costco | requests, curl_cffi |
| bestbuy | requests, curl_cffi |
| staples | curl_cffi |
| walmart | requests, curl_cffi |
| amazon | curl_cffi |

## Steps

Step numbers index `steps` in config/sources.yaml.

| Source | Step | Client | Status | Bytes | Challenge | Payload | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| apple_refurb | 1 | requests | 200 | 347,093 | — | yes | pass |
| apple_refurb | 1 | curl_cffi | 200 | 347,093 | — | yes | pass |
| apple_new | 1 | requests | 200 | 941,197 | — | yes | pass |
| apple_new | 2 | requests | 200 | 1,041,408 | — | yes | pass |
| apple_new | 1 | curl_cffi | 200 | 941,197 | — | yes | pass |
| apple_new | 2 | curl_cffi | 200 | 1,041,408 | — | yes | pass |
| orchard | 1 | requests | 200 | 401,770 | — | yes | pass |
| orchard | 2 | requests | 200 | 789,934 | — | yes | pass |
| orchard | 1 | curl_cffi | 200 | 401,770 | — | yes | pass |
| orchard | 2 | curl_cffi | 200 | 789,934 | — | yes | pass |
| costco | 1 | requests | 200 | 1,875,797 | — | yes | pass |
| costco | 1 | curl_cffi | 200 | 1,875,797 | — | yes | pass |
| bestbuy | 1 | requests | 200 | 160,227 | — | yes | pass |
| bestbuy | 2 | requests | 200 | 160,518 | — | yes | pass |
| bestbuy | 3 | requests | 200 | 11,241 | — | yes | pass |
| bestbuy | 4 | requests | 200 | 786 | — | yes | pass |
| bestbuy | 1 | curl_cffi | 200 | 160,227 | — | yes | pass |
| bestbuy | 2 | curl_cffi | 200 | 160,518 | — | yes | pass |
| bestbuy | 3 | curl_cffi | 200 | 11,241 | — | yes | pass |
| bestbuy | 4 | curl_cffi | 200 | 786 | — | yes | pass |
| staples | 1 | requests | 403 | 6,067 | Just a moment | no | FAIL |
| staples | 1 | curl_cffi | 200 | 43,570 | — | yes | pass |
| walmart | 1 | requests | 200 | 427,309 | — | yes | pass |
| walmart | 2 | requests | 200 | 306,104 | — | yes | pass |
| walmart | 1 | curl_cffi | 200 | 426,583 | — | yes | pass |
| walmart | 2 | curl_cffi | 200 | 306,130 | — | yes | pass |
| amazon | 1 | requests | 503 | 314 | — | no | FAIL |
| amazon | 1 | curl_cffi | 200 | 33,037 | — | yes | pass |
