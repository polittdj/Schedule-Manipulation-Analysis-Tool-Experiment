# Reference-intake manifest

**Generated — do not hand-edit.** Regenerate with `python tools/intake_manifest.py`;
`tests/guards/test_intake_manifest.py` fails if this file and the tree disagree.

`00_REFERENCE_INTAKE/` holds the **non-CUI** build/parity reference suite the operator committed
under ADR-0151/0152 (CLAUDE.md Law 1 names the boundary: real CUI is only ever a production
schedule loaded into the *deployed* tool). The 2026-08-03 external audit found the bulk upload
arrived with a **name/content rotation** — many files carry an extension their bytes contradict.
This manifest is the measurement of that state, so an *inherited* mislabel can be told apart from
a *new* one, and so a silent content swap in the parity inputs fails a test instead of a hearing.

**Nothing the product reads is affected.** The assets the engine depends on are asserted intact by
the guard test on every run, not merely recorded here.

## The rule

A family is asserted only when the bytes say so — a magic signature, an OOXML part name, an OLE2
stream name, or a *complete* JSON/XML parse. `binary` means "no decisive signal" and is never
called a mismatch; an extension with no standardised signature carries no expectation at all. A
fabricated mismatch would be worse than the drift it chases (Law 2).

### Reconciling with the audit's 89

The 2026-08-03 audit reported **89** mismatches; the rule above yields **99**. The gap is exactly
the two classes the audit did not count, and the arithmetic closes to the file:

| class | files | why this manifest counts it |
| --- | ---: | --- |
| `.XLS` holding an OOXML package | 7 | `.xls` denotes OLE2/BIFF; a zip-packaged |
| | | workbook is `.xlsx`. Same application, wrong container — still a mislabel. |
| `.json` holding prose | 3 | `.json` is the tool's **own Save format**, so this is |
| | | the one mislabel a user could actually hit. |

`99 - 7 - 3 = 89`. Neither count is wrong; this one states its rule and a test re-derives it.

### Known divergence — the two `Project5_TAMPERED.mpp` copies

`00_REFERENCE_INTAKE/Project5_TAMPERED.mpp` and `00_REFERENCE_INTAKE/mpp/Project5_TAMPERED.mpp`
are the **same size with different bytes** (102 of 817,152 differ — 0.0125%). The audit recorded
this file as tracked twice and did not report that the copies diverge. Measured, not assumed: the
differing runs sit entirely in the OLE2 **VBA-project storage**; converted through MPXJ both yield
MSPDI identical but for `<CurrentDate>` (the conversion clock), and through the product importer
both yield an equal `Schedule` — 145 tasks, identical calendars, identical CPM timings, the same
4-task critical path (ADR-0112's authoritative 4-stored-critical file) and the same project
finish. **No parity exposure**, and both hashes are pinned below so a future change is not silent.
`mpp/Project5.mpp` is byte-identical to `mpp/Project5_TAMPERED.mpp` — the duplication
`00_REFERENCE_INTAKE/FILE-NAMES.md` documents.

## Summary

| measure | value |
| --- | ---: |
| tracked files | 442 |
| total bytes | 432,842,925 |
| extension&harr;content mismatches | 99 |
| duplicate-content groups | 28 |
| files in a duplicate group | 66 |

### Detected content families

| family | files |
| --- | ---: |
| `empty` | 7 |
| `gzip` | 7 |
| `html` | 10 |
| `ico` | 1 |
| `jpeg` | 49 |
| `json` | 12 |
| `mp4` | 2 |
| `ole2-ppt` | 1 |
| `ole2-project` | 29 |
| `ooxml-excel` | 98 |
| `ooxml-ppt` | 1 |
| `ooxml-word` | 15 |
| `pdf` | 23 |
| `png` | 65 |
| `riff` | 1 |
| `text` | 95 |
| `xml` | 19 |
| `zip` | 7 |

## Extension&harr;content mismatches

99 tracked files declare an extension their bytes contradict.

| declared | actual family | files |
| --- | --- | ---: |
| `.css` | `json` | 2 |
| `.css` | `png` | 1 |
| `.docx` | `json` | 1 |
| `.docx` | `pdf` | 1 |
| `.docx` | `text` | 1 |
| `.html` | `mp4` | 1 |
| `.html` | `ooxml-word` | 1 |
| `.html` | `png` | 1 |
| `.html` | `text` | 1 |
| `.ico` | `text` | 1 |
| `.js` | `ico` | 1 |
| `.js` | `jpeg` | 2 |
| `.js` | `json` | 1 |
| `.json` | `text` | 3 |
| `.md` | `png` | 4 |
| `.md` | `riff` | 1 |
| `.mp4` | `ooxml-word` | 1 |
| `.mp4` | `png` | 1 |
| `.pdf` | `text` | 1 |
| `.png` | `html` | 5 |
| `.png` | `jpeg` | 44 |
| `.png` | `json` | 2 |
| `.png` | `mp4` | 1 |
| `.png` | `pdf` | 1 |
| `.png` | `text` | 10 |
| `.txt` | `html` | 1 |
| `.txt` | `ooxml-word` | 2 |
| `.xls` | `ooxml-excel` | 7 |

| path | size | actual family | sha256 |
| --- | ---: | --- | --- |
| `00_REFERENCE_INTAKE/01-apollo.png` | 1,068,787 | `html` | `738120417fa5939dde29d4afc9d6c7b781d6c04dc5326023e72d017d7e3b8083` |
| `00_REFERENCE_INTAKE/01-console.png` | 159,063 | `html` | `3c11a2f155a27b9e2af088e8bf6c1fd4a04ad7ec532d842f01603bb13b7f8c58` |
| `00_REFERENCE_INTAKE/01-dashboard-mid.png` | 51,938 | `html` | `523f22b889f5660606a5dab12b596d734dfdba92b5303b7a6afeeeee30b2cb2c` |
| `00_REFERENCE_INTAKE/01-daylight.png` | 32,209 | `text` | `20e1df65eba6756ffb16be78b2c05dac810b2b63cbec9c41849fde23024f481f` |
| `00_REFERENCE_INTAKE/01-dr-check.png` | 48,794 | `jpeg` | `99e14757aeecb3a48eac4b8b1b9e3e132c067ab149212405fc419aba01c9983f` |
| `00_REFERENCE_INTAKE/01-dr-fields.png` | 47,172 | `jpeg` | `f4c8f15bbe002c7d1df7a2a091a9d827b66651fba89cf8815ca6f45fb1d5f099` |
| `00_REFERENCE_INTAKE/01-drift-check.png` | 47,170 | `jpeg` | `b6a8f43c936d64849ad213b1c4137104c7343e44e33692fa45024bb26a298cdb` |
| `00_REFERENCE_INTAKE/01-drift.png` | 32,986 | `jpeg` | `c73630bc9a68bacdbbe02dad2291329e84f7d721290794805e74f7e54e19ba42` |
| `00_REFERENCE_INTAKE/01-drivers.png` | 51,019 | `jpeg` | `3157b3085788e56901466985181af555488093d5461fce0ef644e2937d16b3f2` |
| `00_REFERENCE_INTAKE/01-explorer.png` | 54,047 | `jpeg` | `713e4ae34ba599c4efe0c40e1b8e374db25862aa487d5d73eb5fae31d1b8ba13` |
| `00_REFERENCE_INTAKE/01-filters.png` | 42,552 | `jpeg` | `242946670d9c9ed67bed4ccf79b147b260f5694becb78f63033c30d0f26405f1` |
| `00_REFERENCE_INTAKE/01-jarvis.png` | 3,182 | `text` | `65228608109b7db28abe73407b64c5df83cb84e82a6f71a80ccb7be69444da6b` |
| `00_REFERENCE_INTAKE/01-screen-b.png` | 2,155 | `text` | `4933a691aae58729a2c5d0b13353119ef49ac6509c3558cc5ed53c19d0ea1334` |
| `00_REFERENCE_INTAKE/01-screen.png` | 756 | `text` | `2b49c790d0c7e6895b8af12dc72abf77306f7a60e011aec407d6a02a44a6272b` |
| `00_REFERENCE_INTAKE/02-console.png` | 47,995 | `jpeg` | `76160482e6c0ed437280afdfdf806cb963aaaeb37df659b77ec299fbd1befce4` |
| `00_REFERENCE_INTAKE/02-ctl-tiles.png` | 48,733 | `jpeg` | `4ec00f974a8f9990f3250cd573d24f83151aa6fecd5b22013701e6574900169f` |
| `00_REFERENCE_INTAKE/02-daylight.png` | 49,072 | `jpeg` | `6a0949a308873f7fb1b56c3e378402babb0fa3a646ef625a84a5b53cc5554180` |
| `00_REFERENCE_INTAKE/02-dr-check.png` | 48,794 | `jpeg` | `99e14757aeecb3a48eac4b8b1b9e3e132c067ab149212405fc419aba01c9983f` |
| `00_REFERENCE_INTAKE/02-dr-fields.png` | 47,156 | `jpeg` | `25baa154295c9dbce2bd5523843c8137d197bd6f81ad4829eef7a8c8a145388d` |
| `00_REFERENCE_INTAKE/02-drift-check.png` | 47,166 | `jpeg` | `a7c81fde7c08ea8244a05433e77401e961e6c6d2030354d10effe7ec81e35ce8` |
| `00_REFERENCE_INTAKE/02-drift.png` | 32,950 | `jpeg` | `06e7dc16c584be232446f4accd90c5e1acd0b6b718f2d3da91fd8be6be79d8f3` |
| `00_REFERENCE_INTAKE/02-drivers.png` | 51,021 | `jpeg` | `4815b89b9aa83f8ea94f91c3d2b4c2ae509b0c0c766a80e98ba41ee24efa162c` |
| `00_REFERENCE_INTAKE/02-explorer.png` | 51,645 | `jpeg` | `980d5cb5ac150dddd0e171b8cbf7b6de8bf326841924a096e0033513ffa1251e` |
| `00_REFERENCE_INTAKE/02-filters.png` | 42,702 | `jpeg` | `a8b130efb7e4b284870466f92da8c1ac21cc0211047c88be901ee118547f8dd0` |
| `00_REFERENCE_INTAKE/02-jarvis.png` | 47,526 | `jpeg` | `5acaa7a1c00d12e64926dc444096858526e1292b84b32fc7d168f11ef86ad882` |
| `00_REFERENCE_INTAKE/02-screen-b.png` | 837 | `text` | `919c7667f2cb217dbbfbc6e358234d8e8fd1c48327d09f248fb008f51da7425f` |
| `00_REFERENCE_INTAKE/02-screen.png` | 6,409 | `text` | `2378b25377c9dd6ee2d7907c4c2a65c97ad9732a4a3c518db1c67a1081981f73` |
| `00_REFERENCE_INTAKE/03-apollo.png` | 54,091 | `jpeg` | `2ed119bb939b74eab2a309ccd22019e7004f2aa9f4626616b39afcbbba035d50` |
| `00_REFERENCE_INTAKE/03-console.png` | 50,743 | `jpeg` | `14662bc2d1e5fc4298d1809f759ab6e8a1269a56148d6ed8a471ab67dbab6ece` |
| `00_REFERENCE_INTAKE/03-daylight.png` | 53,020 | `jpeg` | `0a054941cbf145e389355114018a913494f133a0b60689922ec04903da3fbfae` |
| `00_REFERENCE_INTAKE/03-dr-fields.png` | 48,543 | `jpeg` | `4779c8f532a83319386f231b711ad50aa1601f436e4846c60c09da792cba80f7` |
| `00_REFERENCE_INTAKE/03-drift-check.png` | 50,951 | `jpeg` | `7837628c2bdddf510279e64316430d0bdb4428fc946cfe649739f4dac263bd25` |
| `00_REFERENCE_INTAKE/03-drift.png` | 33,214 | `jpeg` | `f64e9699a17d19f36bf81a3c57db79ef9596653ac518aff3e62aada196610495` |
| `00_REFERENCE_INTAKE/03-explorer.png` | 51,033 | `jpeg` | `3e2470f1a3cf0ee6d7f11f18a22b125f36c1303b95fe4c767e4a9ebe09c81b2c` |
| `00_REFERENCE_INTAKE/03-jarvis.png` | 49,098 | `jpeg` | `b63ba353ea04c2554e4283bc14c5e24f80f63513b889efdcfd1ddb0f7384da69` |
| `00_REFERENCE_INTAKE/03-screen-b.png` | 2,044 | `text` | `c18b5986a3d0c2a8ff30cc4f3cb38a55bc8a527f5380cf5cdebe97c303ea872a` |
| `00_REFERENCE_INTAKE/04-apollo.png` | 53,987 | `jpeg` | `69ef9a550e1d9562faf000efa9a53655af50fcbcb0af22ad8b77447497619875` |
| `00_REFERENCE_INTAKE/04-console.png` | 55,308 | `jpeg` | `d6d29dc6af083b6c5855b1af2efb0f82d985bb0eae88aaa419efd4feba66042b` |
| `00_REFERENCE_INTAKE/04-drift.png` | 33,161 | `jpeg` | `4377f391c539c36273ac7be193f966a2b09483320e4012b2f80a22e5c40ebe8f` |
| `00_REFERENCE_INTAKE/04-screen-b.png` | 506,359 | `html` | `798289c1ec91e746cd6fc45725af971e0a03da290e2fc6937f0c78fd782637af` |
| `00_REFERENCE_INTAKE/04-screen.png` | 24,987 | `text` | `fd621638fcc97b3819eec0b415c211f2edc8455a553707edbc2fb5aba03b8a82` |
| `00_REFERENCE_INTAKE/05-screen.png` | 5,727 | `text` | `47c1fd5c534e9a313bb48915fbdf1a8fc2a1d140d53b0fcb2b86b81b2ee25ae2` |
| `00_REFERENCE_INTAKE/ASTROLABE Command Deck.dc.html` | 310,267 | `png` | `898dae2a9d66d9f2f225a7180b59a09022593ad38f8cfffe4d61ec4379109dd9` |
| `00_REFERENCE_INTAKE/ASTROLABE.dc.html` | 11,579,637 | `mp4` | `76a2ed782f76e978ef71b9e9f4fb6fb691c89f6d6bc6e4cdca015ec2e80ba46d` |
| `00_REFERENCE_INTAKE/CLAUDE-CODE-HANDOFF.md` | 622,463 | `png` | `e872aa3eaa02bc8ee62f1d4c51badb92fb69570608e44ee17547df23a0bbe888` |
| `00_REFERENCE_INTAKE/Concepts, Methods & Techniques-272662cf.docx` | 20,339 | `text` | `9d8b8ad6248b7bc553ac2a15b319ddd5bea193e7fe826cee8a41518254d3d57c` |
| `00_REFERENCE_INTAKE/DESIGN-GUIDE.md` | 752,246 | `png` | `1d4990ed7da7d4f0fcfba5700a8aed1382813b7660d8fc72530efc8bc0d71a56` |
| `00_REFERENCE_INTAKE/Mission Ops Redesign v2.dc (1).html` | 44,316 | `ooxml-word` | `272662cf43015e28d4db365c9425b3daebc9acc7ac9a4a8533fe67035795d34c` |
| `00_REFERENCE_INTAKE/README (2).md` | 21,413 | `png` | `48a7698844feb0326af085b1d8b6f03bfde5dd66bb98485f705754b9203c760a` |
| `00_REFERENCE_INTAKE/README.md` | 605,604 | `png` | `2bcb921f2a24bb7446ad7e0b4ae7b790c54aab5bdf2cb83b2a4bdc5ca0806a5e` |
| `00_REFERENCE_INTAKE/Recording 2026-07-27 150631.mp4` | 44,316 | `ooxml-word` | `272662cf43015e28d4db365c9425b3daebc9acc7ac9a4a8533fe67035795d34c` |
| `00_REFERENCE_INTAKE/_ds_manifest.json` | 5,336 | `text` | `4a0a2b673c7eefbbd2f430619f8c09c5f89731d166459b8380a7cc6698f5dbd4` |
| `00_REFERENCE_INTAKE/a11y.js` | 3,050 | `json` | `d8bbddfd14511eb93d46173525937e8d446233b7618ac1e9c0fc1204b950dfba` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HA296F~1.XLS` | 258,951 | `ooxml-excel` | `edc37a87ca9670935829e4fe14faa9bd04da8bf8c80c465c0bcf2b2cf6818140` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HA3755~1.XLS` | 21,059 | `ooxml-excel` | `088a4a3e9a05b077548a5e61f22435341863bb88a205d4b6f40400c392393688` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HA7B01~1.XLS` | 496,770 | `ooxml-excel` | `7b863cbe28529b7dfee9967f6d9a850f0b0152af19ff6d76939492f3676bdc21` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HA88CE~1.XLS` | 90,187 | `ooxml-excel` | `26e26bfa957c2076543083a011658e1a34d05458eee34763eb3c8e833d6988fb` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HA95A8~1.XLS` | 496,627 | `ooxml-excel` | `3ab684888ac318ce47b92510705418d5a987c764ccb1dbfe635399f5fd29d314` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HARD_F~3.XLS` | 258,865 | `ooxml-excel` | `52847764bd77319741a652f059c0be91e6f302d349547b2106e6fca2eaa3b66e` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HARD_F~4.XLS` | 30,693 | `ooxml-excel` | `3e612f369e7375c8f774ac357343e18d4ca04346e1ee315424190a993a30e0f3` |
| `00_REFERENCE_INTAKE/advanced_sra.pdf` | 8,999 | `text` | `22a5207e7f8dca0304c6303d9173623f83f8e879a1ba44cd6ac2cb7dca43b82d` |
| `00_REFERENCE_INTAKE/advanced_sra.txt` | 54,180 | `html` | `6d5befe849cd83720f30e850f4dcb68e12305568d1cda86f3e76d4d587bc4190` |
| `00_REFERENCE_INTAKE/beyond.png` | 51,013 | `jpeg` | `0b0363d5f20f7e69e09d0289b19fe43fd3ee042ed9ebe1a134bc72f2a523cdd0` |
| `00_REFERENCE_INTAKE/briefing.png` | 60,404 | `jpeg` | `3fc019608399c9606e8e97db1bd5b77439544e5f06de7e1afc30fb7f8ec861ea` |
| `00_REFERENCE_INTAKE/ch01-drill.png` | 51,503 | `jpeg` | `7b43c4bafc880113f43c6c54feaba7f5bd63b719d35987b8809e6ed42110c142` |
| `00_REFERENCE_INTAKE/concepts_a.docx` | 11,625,699 | `pdf` | `859faf30473a3c062383c3b174fef9bc7b867b442b991ae75ff166a29485d855` |
| `00_REFERENCE_INTAKE/concepts_b.docx` | 4,863 | `json` | `98414cd9834f6f5499465227150e6ef437fe0e37ce6416a46e3b70c79148a505` |
| `00_REFERENCE_INTAKE/concepts_b.txt` | 44,316 | `ooxml-word` | `272662cf43015e28d4db365c9425b3daebc9acc7ac9a4a8533fe67035795d34c` |
| `00_REFERENCE_INTAKE/crispness-scan.json` | 34,965 | `text` | `153e2e6e573e729b4e3e328cd5e6babff6f6b4422904273b23575d8d4ad6636b` |
| `00_REFERENCE_INTAKE/ctl-check.png` | 36,001 | `jpeg` | `830da29c97132c7c9627679157d578f5b7ab98dc2f348fe7442bca74357a5b8a` |
| `00_REFERENCE_INTAKE/ctl-tiles.png` | 47,629 | `jpeg` | `6ea84c5e570d38cfb1fece3383548d1093ba35e5128186dd48bd622669794b48` |
| `00_REFERENCE_INTAKE/ctl-tiles2.png` | 47,629 | `jpeg` | `6ea84c5e570d38cfb1fece3383548d1093ba35e5128186dd48bd622669794b48` |
| `00_REFERENCE_INTAKE/draw-54db3784-3574-41e9-be5b-7d9249f2254c.png` | 806,741 | `pdf` | `1eafe822ff106f7fe6d11f7edb8cea2ebfc8f4ddb049d5488202e1375d9807f5` |
| `00_REFERENCE_INTAKE/draw-81bf283a-dbd7-4066-8596-672a9d3322a1.png` | 1,065,588 | `html` | `9edeb4793d834016cb6c90b159dfda8d75f030828c86ace36b62be1010b01ca0` |
| `00_REFERENCE_INTAKE/draw-b3e46260-3387-4693-85dc-8f3ed9a032db.png` | 3,923,990 | `mp4` | `317861011db5d27a30de622f5ad85e0c3295d729e54063c01fb04bc5c77d67ef` |
| `00_REFERENCE_INTAKE/favicon.ico` | 4,979 | `text` | `7ecee81505889d361196ecaa275d03c60c7589627fc818166e9186582532dcfa` |
| `00_REFERENCE_INTAKE/forms.css` | 26,274 | `json` | `ddc3f8d3eccb909544ce010ac05d3ab5a830563fdcdfe77d0e660e5e9dc83077` |
| `00_REFERENCE_INTAKE/github.md` | 20,208 | `riff` | `e766224e24d38bb1f743c85f77e3055ece163a1f17c4cdfafeff5999f0a17b4b` |
| `00_REFERENCE_INTAKE/guide.png` | 48,794 | `jpeg` | `99e14757aeecb3a48eac4b8b1b9e3e132c067ab149212405fc419aba01c9983f` |
| `00_REFERENCE_INTAKE/heartbeat.js` | 8,800 | `ico` | `b807bc3201fd6e28a90f32a97922798b35a10e029903af8db73110b47d3c61ef` |
| `00_REFERENCE_INTAKE/instruments.css` | 48,479 | `json` | `4ff9aa9ff95871f308d803768a261b18e8baf32ab85b1c24e90d955c81b69b18` |
| `00_REFERENCE_INTAKE/int02_advanced.txt` | 44,316 | `ooxml-word` | `272662cf43015e28d4db365c9425b3daebc9acc7ac9a4a8533fe67035795d34c` |
| `00_REFERENCE_INTAKE/it-outline.png` | 46,484 | `jpeg` | `d3e1f5f33aadc162fadf8e88e25c339bda8a6a66b14c09be2b8576618cf232e9` |
| `00_REFERENCE_INTAKE/it-outline2.png` | 52,223 | `jpeg` | `527562c908a091b9a4599694cf40ef0d941460cc675efd1888304c7a00fa2d56` |
| `00_REFERENCE_INTAKE/metric-lab-2.png` | 52,248 | `jpeg` | `ad575c08826c8a53a799a13bdca475f5ba70f5947e1f306154fb5e8090f1ac47` |
| `00_REFERENCE_INTAKE/metric-lab-3.png` | 57,728 | `jpeg` | `c3015fd6e03b3510cedcd906541c69ef6db16f62cd85e9e578a98ef203794b24` |
| `00_REFERENCE_INTAKE/metric-lab.png` | 57,623 | `jpeg` | `b386f4ec014d87e50b04227f2c3266ef29cb6be5abe758cb31eb995337616a68` |
| `00_REFERENCE_INTAKE/mock-analysis.js` | 24,167 | `jpeg` | `32a4f50b19adb690afd660f766c623c538f66f43e6b83749f926f2b6eb3c8c83` |
| `00_REFERENCE_INTAKE/mock-api.js` | 35,937 | `jpeg` | `5d0b19a9da8261c5ed2bfca0881557a0028cbac6a333f9d6c4f949e776b065b2` |
| `00_REFERENCE_INTAKE/overlap.png` | 57,642 | `jpeg` | `42876758eb2395bdb60332591f644989bde9e42a469657bbefb2b67f64ac3a1e` |
| `00_REFERENCE_INTAKE/probe-analysis.html` | 38,325 | `text` | `808fc682b1f8d87af901197b457d19823fe9737d80908dd14a6729dbe4bcd843` |
| `00_REFERENCE_INTAKE/reel-f0.png` | 11,398 | `json` | `2c4bb563b1150ab6d81e2ac297fe0d5ee3a8394f48acf593814036b3877385e6` |
| `00_REFERENCE_INTAKE/reel-f1.png` | 27,691 | `text` | `f39ca79076ee5488396bdfedc18a0c2f4ba899f4acde7fb237da7449df21b964` |
| `00_REFERENCE_INTAKE/reel-f2.png` | 41,751 | `json` | `f02d1645cdb20a89ac28057061e08ae5ae80220a323b34bf176cb78a6bad0f66` |
| `00_REFERENCE_INTAKE/reel_shot-1785179231876.mp4` | 267,519 | `png` | `9ed1e74ed206966b95fbad52807e12b4bc476fcb7b092d0f87ccc0723285efd6` |
| `00_REFERENCE_INTAKE/repo-audit.json` | 34,965 | `text` | `153e2e6e573e729b4e3e328cd5e6babff6f6b4422904273b23575d8d4ad6636b` |
| `00_REFERENCE_INTAKE/seg-forecast-2.png` | 48,868 | `jpeg` | `27190b4563646bdca5533a1355a21fc4ad272fec3031fd4c9d93369cbd225c1f` |
| `00_REFERENCE_INTAKE/seg-forecast.png` | 61,546 | `jpeg` | `28c045d356b084a2511fc76836f8565534e5a6a4e5530cb4f6b421db2769a566` |
| `00_REFERENCE_INTAKE/sf-themes.css` | 438,326 | `png` | `01937250b32df6b787ec66a667e07dae3ce750db777e60c194532b28a1716ec9` |

## Duplicate-content groups

Files sharing a SHA-256. This is the rotation's signature: a bulk upload that reused one
body under several names, not random corruption.

| sha256 | files | paths |
| --- | ---: | --- |
| `e3b0c44298fc1c14…` | 7 | `00_REFERENCE_INTAKE/.gitkeep`<br>`00_REFERENCE_INTAKE/acumen_v8.11.0/.gitkeep`<br>`00_REFERENCE_INTAKE/metrics_library/.gitkeep`<br>`00_REFERENCE_INTAKE/mpp/.gitkeep`<br>`00_REFERENCE_INTAKE/pbix/.gitkeep`<br>`00_REFERENCE_INTAKE/references/.gitkeep`<br>`00_REFERENCE_INTAKE/ssi/.gitkeep` |
| `272662cf43015e28…` | 5 | `00_REFERENCE_INTAKE/Mission Ops Redesign v2.dc (1).html`<br>`00_REFERENCE_INTAKE/Recording 2026-07-27 150631.mp4`<br>`00_REFERENCE_INTAKE/concepts_b.txt`<br>`00_REFERENCE_INTAKE/int02_advanced.txt`<br>`00_REFERENCE_INTAKE/references/Concepts, Methods & Techniques.docx` |
| `99e14757aeecb3a4…` | 3 | `00_REFERENCE_INTAKE/01-dr-check.png`<br>`00_REFERENCE_INTAKE/02-dr-check.png`<br>`00_REFERENCE_INTAKE/guide.png` |
| `b2f9db8d81491760…` | 3 | `00_REFERENCE_INTAKE/ssi/sra-Polaris Finish Date Confidence S-Curve Results Large Test File2.xlsx`<br>`00_REFERENCE_INTAKE/ssi/sra-Polaris Risk Drivers Tornado Results Large Test File2.xlsx`<br>`00_REFERENCE_INTAKE/ssi/sra-Polaris Sensitivity Results Large Test File2.xlsx` |
| `0d1ab6f3b684143d…` | 2 | `00_REFERENCE_INTAKE/mpp/Project5.mpp`<br>`00_REFERENCE_INTAKE/mpp/Project5_TAMPERED.mpp` |
| `14547256bf8c83b7…` | 2 | `00_REFERENCE_INTAKE/PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx`<br>`00_REFERENCE_INTAKE/references/PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx` |
| `153e2e6e573e729b…` | 2 | `00_REFERENCE_INTAKE/crispness-scan.json`<br>`00_REFERENCE_INTAKE/repo-audit.json` |
| `1eafe822ff106f7f…` | 2 | `00_REFERENCE_INTAKE/draw-54db3784-3574-41e9-be5b-7d9249f2254c.png`<br>`00_REFERENCE_INTAKE/references/INT-02-Advanced-Schedule-Analysis.pdf` |
| `2cbe6825e36abcbd…` | 2 | `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/HARDENED_CORPUS_CROSS_REFERENCE.xlsx`<br>`00_REFERENCE_INTAKE/references/HARDENED_CORPUS_CROSS_REFERENCE.xlsx` |
| `2fcdad6143ab5ddf…` | 2 | `00_REFERENCE_INTAKE/Project2.mpp`<br>`00_REFERENCE_INTAKE/mpp/Project2.mpp` |
| `31360e10aa89bd28…` | 2 | `00_REFERENCE_INTAKE/SP-20240014019.pdf`<br>`00_REFERENCE_INTAKE/references/SP-20240014019.pdf` |
| `3c11a2f155a27b9e…` | 2 | `00_REFERENCE_INTAKE/01-console.png`<br>`00_REFERENCE_INTAKE/Mission Ops Redesign.dc.html` |
| `42c68ad040389875…` | 2 | `00_REFERENCE_INTAKE/pm-handbook-nasa-sp-2014-3705-2024jun.pdf`<br>`00_REFERENCE_INTAKE/references/pm-handbook-nasa-sp-2014-3705-2024jun.pdf` |
| `48f7294a3c6d279d…` | 2 | `00_REFERENCE_INTAKE/references/schedule-management-handbook-20240315-update.zip`<br>`00_REFERENCE_INTAKE/schedule-management-handbook-20240315-update.zip` |
| `4cd6b6d0afd1c0f2…` | 2 | `00_REFERENCE_INTAKE/SP-20240014326.pdf`<br>`00_REFERENCE_INTAKE/references/SP-20240014326.pdf` |
| `579486fb3c1a398d…` | 2 | `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_AND_ORACLE_TEST_PROTOCOL.docx`<br>`00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/HARDENED_AUDIT_AND_ORACLE_TEST_PROTOCOL.docx` |
| `67f7a9e411ae2878…` | 2 | `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_AND_ORACLE_TEST_PROTOCOL.md`<br>`00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/HARDENED_AUDIT_AND_ORACLE_TEST_PROTOCOL.md` |
| `6ea84c5e570d38cf…` | 2 | `00_REFERENCE_INTAKE/ctl-tiles.png`<br>`00_REFERENCE_INTAKE/ctl-tiles2.png` |
| `6f7da7e5e099d249…` | 2 | `00_REFERENCE_INTAKE/evmimplementationhandbook-1-1.pdf`<br>`00_REFERENCE_INTAKE/references/evmimplementationhandbook-1-1.pdf` |
| `738120417fa5939d…` | 2 | `00_REFERENCE_INTAKE/01-apollo.png`<br>`00_REFERENCE_INTAKE/Mission Ops Redesign v2.dc.html` |
| `73c0a47635465b31…` | 2 | `00_REFERENCE_INTAKE/references/srb-handbook-official-rev-c-202301243-final-v2.pdf`<br>`00_REFERENCE_INTAKE/srb-handbook-official-rev-c-202301243-final-v2.pdf` |
| `834e68133874ce73…` | 2 | `00_REFERENCE_INTAKE/Project5_TAMPERED_UID_67_Directional_Path_Analysis_2026-7-8-8-19-10.xlsx`<br>`00_REFERENCE_INTAKE/ssi/Project5_TAMPERED_UID_67_Directional_Path_Analysis_2026-7-8-8-19-10.xlsx` |
| `859faf30473a3c06…` | 2 | `00_REFERENCE_INTAKE/INT-02-Advanced-Schedule-Analysis.pdf`<br>`00_REFERENCE_INTAKE/concepts_a.docx` |
| `90f63f49ed287c05…` | 2 | `00_REFERENCE_INTAKE/nasa-wbs-handbook.pdf`<br>`00_REFERENCE_INTAKE/references/nasa-wbs-handbook.pdf` |
| `b67f02e49e5f9483…` | 2 | `00_REFERENCE_INTAKE/Large_Test_File_UID_152_Directional_Path_Analysis_2026-7-8-8-45-50.xlsx`<br>`00_REFERENCE_INTAKE/ssi/Large_Test_File_UID_152_Directional_Path_Analysis_2026-7-8-8-45-50.xlsx` |
| `b9105a99df970143…` | 2 | `00_REFERENCE_INTAKE/references/sopi_6.0_final.pdf`<br>`00_REFERENCE_INTAKE/sopi_6.0_final.pdf` |
| `d36d9776cb1b2b45…` | 2 | `00_REFERENCE_INTAKE/ppc-handbook-1-5-17.pdf`<br>`00_REFERENCE_INTAKE/references/ppc-handbook-1-5-17.pdf` |
| `fd1b310f4b4e3f45…` | 2 | `00_REFERENCE_INTAKE/nasa-ibr-handbook-5-1.pdf`<br>`00_REFERENCE_INTAKE/references/nasa-ibr-handbook-5-1.pdf` |

## Full inventory

| path | size | ext | family | mismatch | sha256 |
| --- | ---: | --- | --- | :-: | --- |
| `00_REFERENCE_INTAKE/# Schedule Forensics — Roles & Orch.txt` | 9,913 | `.txt` | `text` | — | `3e781e8ddab30c1984e1204e02074c3bb09c6e195032e5c30dde42bffaf92d96` |
| `00_REFERENCE_INTAKE/.gitkeep` | 0 | `(none)` | `empty` | — | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `00_REFERENCE_INTAKE/01-apollo.png` | 1,068,787 | `.png` | `html` | **yes** | `738120417fa5939dde29d4afc9d6c7b781d6c04dc5326023e72d017d7e3b8083` |
| `00_REFERENCE_INTAKE/01-console.png` | 159,063 | `.png` | `html` | **yes** | `3c11a2f155a27b9e2af088e8bf6c1fd4a04ad7ec532d842f01603bb13b7f8c58` |
| `00_REFERENCE_INTAKE/01-dashboard-mid.png` | 51,938 | `.png` | `html` | **yes** | `523f22b889f5660606a5dab12b596d734dfdba92b5303b7a6afeeeee30b2cb2c` |
| `00_REFERENCE_INTAKE/01-daylight.png` | 32,209 | `.png` | `text` | **yes** | `20e1df65eba6756ffb16be78b2c05dac810b2b63cbec9c41849fde23024f481f` |
| `00_REFERENCE_INTAKE/01-dr-check.png` | 48,794 | `.png` | `jpeg` | **yes** | `99e14757aeecb3a48eac4b8b1b9e3e132c067ab149212405fc419aba01c9983f` |
| `00_REFERENCE_INTAKE/01-dr-fields.png` | 47,172 | `.png` | `jpeg` | **yes** | `f4c8f15bbe002c7d1df7a2a091a9d827b66651fba89cf8815ca6f45fb1d5f099` |
| `00_REFERENCE_INTAKE/01-drift-check.png` | 47,170 | `.png` | `jpeg` | **yes** | `b6a8f43c936d64849ad213b1c4137104c7343e44e33692fa45024bb26a298cdb` |
| `00_REFERENCE_INTAKE/01-drift.png` | 32,986 | `.png` | `jpeg` | **yes** | `c73630bc9a68bacdbbe02dad2291329e84f7d721290794805e74f7e54e19ba42` |
| `00_REFERENCE_INTAKE/01-drivers.png` | 51,019 | `.png` | `jpeg` | **yes** | `3157b3085788e56901466985181af555488093d5461fce0ef644e2937d16b3f2` |
| `00_REFERENCE_INTAKE/01-explorer.png` | 54,047 | `.png` | `jpeg` | **yes** | `713e4ae34ba599c4efe0c40e1b8e374db25862aa487d5d73eb5fae31d1b8ba13` |
| `00_REFERENCE_INTAKE/01-filters.png` | 42,552 | `.png` | `jpeg` | **yes** | `242946670d9c9ed67bed4ccf79b147b260f5694becb78f63033c30d0f26405f1` |
| `00_REFERENCE_INTAKE/01-jarvis.png` | 3,182 | `.png` | `text` | **yes** | `65228608109b7db28abe73407b64c5df83cb84e82a6f71a80ccb7be69444da6b` |
| `00_REFERENCE_INTAKE/01-screen-b.png` | 2,155 | `.png` | `text` | **yes** | `4933a691aae58729a2c5d0b13353119ef49ac6509c3558cc5ed53c19d0ea1334` |
| `00_REFERENCE_INTAKE/01-screen.png` | 756 | `.png` | `text` | **yes** | `2b49c790d0c7e6895b8af12dc72abf77306f7a60e011aec407d6a02a44a6272b` |
| `00_REFERENCE_INTAKE/02-console.png` | 47,995 | `.png` | `jpeg` | **yes** | `76160482e6c0ed437280afdfdf806cb963aaaeb37df659b77ec299fbd1befce4` |
| `00_REFERENCE_INTAKE/02-ctl-tiles.png` | 48,733 | `.png` | `jpeg` | **yes** | `4ec00f974a8f9990f3250cd573d24f83151aa6fecd5b22013701e6574900169f` |
| `00_REFERENCE_INTAKE/02-daylight.png` | 49,072 | `.png` | `jpeg` | **yes** | `6a0949a308873f7fb1b56c3e378402babb0fa3a646ef625a84a5b53cc5554180` |
| `00_REFERENCE_INTAKE/02-dr-check.png` | 48,794 | `.png` | `jpeg` | **yes** | `99e14757aeecb3a48eac4b8b1b9e3e132c067ab149212405fc419aba01c9983f` |
| `00_REFERENCE_INTAKE/02-dr-fields.png` | 47,156 | `.png` | `jpeg` | **yes** | `25baa154295c9dbce2bd5523843c8137d197bd6f81ad4829eef7a8c8a145388d` |
| `00_REFERENCE_INTAKE/02-drift-check.png` | 47,166 | `.png` | `jpeg` | **yes** | `a7c81fde7c08ea8244a05433e77401e961e6c6d2030354d10effe7ec81e35ce8` |
| `00_REFERENCE_INTAKE/02-drift.png` | 32,950 | `.png` | `jpeg` | **yes** | `06e7dc16c584be232446f4accd90c5e1acd0b6b718f2d3da91fd8be6be79d8f3` |
| `00_REFERENCE_INTAKE/02-drivers.png` | 51,021 | `.png` | `jpeg` | **yes** | `4815b89b9aa83f8ea94f91c3d2b4c2ae509b0c0c766a80e98ba41ee24efa162c` |
| `00_REFERENCE_INTAKE/02-explorer.png` | 51,645 | `.png` | `jpeg` | **yes** | `980d5cb5ac150dddd0e171b8cbf7b6de8bf326841924a096e0033513ffa1251e` |
| `00_REFERENCE_INTAKE/02-filters.png` | 42,702 | `.png` | `jpeg` | **yes** | `a8b130efb7e4b284870466f92da8c1ac21cc0211047c88be901ee118547f8dd0` |
| `00_REFERENCE_INTAKE/02-jarvis.png` | 47,526 | `.png` | `jpeg` | **yes** | `5acaa7a1c00d12e64926dc444096858526e1292b84b32fc7d168f11ef86ad882` |
| `00_REFERENCE_INTAKE/02-screen-b.png` | 837 | `.png` | `text` | **yes** | `919c7667f2cb217dbbfbc6e358234d8e8fd1c48327d09f248fb008f51da7425f` |
| `00_REFERENCE_INTAKE/02-screen.png` | 6,409 | `.png` | `text` | **yes** | `2378b25377c9dd6ee2d7907c4c2a65c97ad9732a4a3c518db1c67a1081981f73` |
| `00_REFERENCE_INTAKE/03-apollo.png` | 54,091 | `.png` | `jpeg` | **yes** | `2ed119bb939b74eab2a309ccd22019e7004f2aa9f4626616b39afcbbba035d50` |
| `00_REFERENCE_INTAKE/03-console.png` | 50,743 | `.png` | `jpeg` | **yes** | `14662bc2d1e5fc4298d1809f759ab6e8a1269a56148d6ed8a471ab67dbab6ece` |
| `00_REFERENCE_INTAKE/03-daylight.png` | 53,020 | `.png` | `jpeg` | **yes** | `0a054941cbf145e389355114018a913494f133a0b60689922ec04903da3fbfae` |
| `00_REFERENCE_INTAKE/03-dr-fields.png` | 48,543 | `.png` | `jpeg` | **yes** | `4779c8f532a83319386f231b711ad50aa1601f436e4846c60c09da792cba80f7` |
| `00_REFERENCE_INTAKE/03-drift-check.png` | 50,951 | `.png` | `jpeg` | **yes** | `7837628c2bdddf510279e64316430d0bdb4428fc946cfe649739f4dac263bd25` |
| `00_REFERENCE_INTAKE/03-drift.png` | 33,214 | `.png` | `jpeg` | **yes** | `f64e9699a17d19f36bf81a3c57db79ef9596653ac518aff3e62aada196610495` |
| `00_REFERENCE_INTAKE/03-explorer.png` | 51,033 | `.png` | `jpeg` | **yes** | `3e2470f1a3cf0ee6d7f11f18a22b125f36c1303b95fe4c767e4a9ebe09c81b2c` |
| `00_REFERENCE_INTAKE/03-jarvis.png` | 49,098 | `.png` | `jpeg` | **yes** | `b63ba353ea04c2554e4283bc14c5e24f80f63513b889efdcfd1ddb0f7384da69` |
| `00_REFERENCE_INTAKE/03-screen-b.png` | 2,044 | `.png` | `text` | **yes** | `c18b5986a3d0c2a8ff30cc4f3cb38a55bc8a527f5380cf5cdebe97c303ea872a` |
| `00_REFERENCE_INTAKE/04-apollo.png` | 53,987 | `.png` | `jpeg` | **yes** | `69ef9a550e1d9562faf000efa9a53655af50fcbcb0af22ad8b77447497619875` |
| `00_REFERENCE_INTAKE/04-console.png` | 55,308 | `.png` | `jpeg` | **yes** | `d6d29dc6af083b6c5855b1af2efb0f82d985bb0eae88aaa419efd4feba66042b` |
| `00_REFERENCE_INTAKE/04-drift.png` | 33,161 | `.png` | `jpeg` | **yes** | `4377f391c539c36273ac7be193f966a2b09483320e4012b2f80a22e5c40ebe8f` |
| `00_REFERENCE_INTAKE/04-jarvis.png` | 28,786 | `.png` | `png` | — | `40ada5e7deea8899a4ef66ddbd48c369fb37348e815274bd2fe02b326fb78555` |
| `00_REFERENCE_INTAKE/04-screen-b.png` | 506,359 | `.png` | `html` | **yes** | `798289c1ec91e746cd6fc45725af971e0a03da290e2fc6937f0c78fd782637af` |
| `00_REFERENCE_INTAKE/04-screen.png` | 24,987 | `.png` | `text` | **yes** | `fd621638fcc97b3819eec0b415c211f2edc8455a553707edbc2fb5aba03b8a82` |
| `00_REFERENCE_INTAKE/05-apollo.png` | 29,623 | `.png` | `png` | — | `135082baf7b000bdcdc90fa743529cdc03666967ce26666976edb7d5e63d9194` |
| `00_REFERENCE_INTAKE/05-console.png` | 24,847 | `.png` | `png` | — | `cd11e32f0e868cfd587a12d8a01b7af80f718e4e9dc113e517004208e66c958f` |
| `00_REFERENCE_INTAKE/05-daylight.png` | 39,056 | `.png` | `png` | — | `f769a7502b78ed01d93e818f01533dbfbebefee91dcd39a44481f679e74cb02a` |
| `00_REFERENCE_INTAKE/05-jarvis.png` | 30,588 | `.png` | `png` | — | `45cad3630e2a22196854bc333cd4251371e15fcfef544f813471b3c6fbd8da95` |
| `00_REFERENCE_INTAKE/05-screen.png` | 5,727 | `.png` | `text` | **yes** | `47c1fd5c534e9a313bb48915fbdf1a8fc2a1d140d53b0fcb2b86b81b2ee25ae2` |
| `00_REFERENCE_INTAKE/06-apollo.png` | 29,702 | `.png` | `png` | — | `cabe3f4dd7abac3423002df7de7d3fb1d7ba2e48957470bacc8ba8401e15c0af` |
| `00_REFERENCE_INTAKE/06-console.png` | 24,804 | `.png` | `png` | — | `e13db835d827b434e61e1a2237b4142e7a75dccbf96ed3c5027d3f62086064dd` |
| `00_REFERENCE_INTAKE/06-daylight.png` | 42,657 | `.png` | `png` | — | `29e9ccdfec20877c2865954a31b189f78a280df71cc48185e372e688f48e2327` |
| `00_REFERENCE_INTAKE/06-jarvis.png` | 31,914 | `.png` | `png` | — | `f1dd69fea9ca70d89e84db6e6b0ee4d7f4eb0a631e33f10103bc4605336c324c` |
| `00_REFERENCE_INTAKE/07-apollo.png` | 30,676 | `.png` | `png` | — | `2d9699f3fe899ceffe490845b1c23d172b40a405dccff5f79966f5bb471b37e0` |
| `00_REFERENCE_INTAKE/07-console.png` | 27,799 | `.png` | `png` | — | `69e319a33a4caa1d7570e8d7d9f665ad1491e7f97f4b2916fe1a62423bb4b571` |
| `00_REFERENCE_INTAKE/07-daylight.png` | 46,802 | `.png` | `png` | — | `c74765bcd0ae52fa0cb147e9061b86d89e40022e9e4330e45ba591b64a3ef2db` |
| `00_REFERENCE_INTAKE/07-jarvis.png` | 31,298 | `.png` | `png` | — | `7ce798dd0118e6cee32b120476b4dafc2d50e00eaf989d5f6eb7b5a8525cbd76` |
| `00_REFERENCE_INTAKE/08-apollo.png` | 30,971 | `.png` | `png` | — | `cfdacffd8dbc76d0b4a05b9ae49c64e2f76ebd19099f3c17ec9c082b0d61a316` |
| `00_REFERENCE_INTAKE/08-console.png` | 27,796 | `.png` | `png` | — | `c520be13f42ca8bfe63775f21e00195d45cc75658fa263bf9d84057503b080af` |
| `00_REFERENCE_INTAKE/08-daylight.png` | 43,207 | `.png` | `png` | — | `3e1c47066a745a04ea6a761f0f171d4409169de359e2141370331cdc45847079` |
| `00_REFERENCE_INTAKE/08-jarvis.png` | 29,577 | `.png` | `png` | — | `3070967856e69b150505f9deb10f21e3d9a2397b40716476be18931f29826a8a` |
| `00_REFERENCE_INTAKE/09-apollo.png` | 32,247 | `.png` | `png` | — | `6101ed06c777b4ee6c629a7d002829d887170f062efc1e7dec151a81797be43a` |
| `00_REFERENCE_INTAKE/09-console.png` | 28,039 | `.png` | `png` | — | `a6053a49970d52f8c13b4b095bbfa5e702f8e637a1a18ac5b1afb7f783e9b708` |
| `00_REFERENCE_INTAKE/09-daylight.png` | 39,989 | `.png` | `png` | — | `a61d09529cbb912f568509e1af44a8f6f525cf68c9c375edf5eec023de138d66` |
| `00_REFERENCE_INTAKE/09-jarvis.png` | 26,257 | `.png` | `png` | — | `b41e8057bb9b4a383dca77ff4d2bae25fa19b053ca75e369a3630b0abc549ca3` |
| `00_REFERENCE_INTAKE/10-console.png` | 32,289 | `.png` | `png` | — | `a32b3ac434146311ec45fb162c82411a99f70161ec6b3c92bec8940d6a9d0442` |
| `00_REFERENCE_INTAKE/10-daylight.png` | 28,081 | `.png` | `png` | — | `17faff223c497a07dfc0ab76dd9c3c758317e26a80076181014f851bc00ed124` |
| `00_REFERENCE_INTAKE/11-console.png` | 37,084 | `.png` | `png` | — | `3604b59d35dde6464d85f8a8e1b7a0b8f2840d9ca640ed3d5e9f0cb885b6b860` |
| `00_REFERENCE_INTAKE/11-daylight.png` | 26,276 | `.png` | `png` | — | `7e73cef7016a2e395a398dc9f467f3c69b3933a6410f76c695d8a0426e7c5850` |
| `00_REFERENCE_INTAKE/12-console.png` | 31,361 | `.png` | `png` | — | `c7662d6b698ad91ea3e3172a7de67cd82559a191eeb181088f323687a4ac0956` |
| `00_REFERENCE_INTAKE/12-daylight.png` | 25,882 | `.png` | `png` | — | `6d489da3af1c433984ce58dbcf36fd9e3d94c9f76650cddfe35659bff6c93a9f` |
| `00_REFERENCE_INTAKE/13-console.png` | 35,233 | `.png` | `png` | — | `a22c44fffb89567a79ec0899f9b669b0f6045cbefc16f37062ab5d5a1e6aad17` |
| `00_REFERENCE_INTAKE/13-daylight.png` | 32,371 | `.png` | `png` | — | `b24e7f12824772439053df5f71934d98c51a1e3d5d1d8d0eace6e545cfd64ca6` |
| `00_REFERENCE_INTAKE/14-console.png` | 31,358 | `.png` | `png` | — | `a19b7e5c126b98105c90ca267b9488cceacbf9489c4d672aadce338cfab5953b` |
| `00_REFERENCE_INTAKE/14-daylight.png` | 25,907 | `.png` | `png` | — | `99f64243c0d906f3b56fc496cc7e6f8c2c605a35ac4b93d069c3c0247e240175` |
| `00_REFERENCE_INTAKE/15-console.png` | 42,314 | `.png` | `png` | — | `ef3b55d8e3dd0a625d37b0cc229d0d73e21bf74d3ae40e7710fda4866cf9a9c4` |
| `00_REFERENCE_INTAKE/15-daylight.png` | 27,371 | `.png` | `png` | — | `86e10e216d515d9c5109e9c0da3f792e34c63b34e208920ad3ee4fd4a36ec21a` |
| `00_REFERENCE_INTAKE/16-console.png` | 29,242 | `.png` | `png` | — | `b3a6d6c77c11a8d406c0e269c1ff6dc71765d6d83810a52aebde27e431058ef5` |
| `00_REFERENCE_INTAKE/16-daylight.png` | 25,208 | `.png` | `png` | — | `83d7ab50a5a365f595552619e2fb205ea089ced309f80559c3db594e63145f4c` |
| `00_REFERENCE_INTAKE/17-console.png` | 38,782 | `.png` | `png` | — | `8204da7b2e1e1d13ad883f4f7001918dd43ba95844df7834977caf002d0b5f32` |
| `00_REFERENCE_INTAKE/17-daylight.png` | 29,215 | `.png` | `png` | — | `8105adfce1addfccb267812c4038ed6df9d349435191512208d1c10bbb8ed9a1` |
| `00_REFERENCE_INTAKE/18-console.png` | 25,231 | `.png` | `png` | — | `dcf5c80846c1971b5a732459727b00cf991b4d3d16a8f148f146d07b6a46cc08` |
| `00_REFERENCE_INTAKE/18-daylight.png` | 26,364 | `.png` | `png` | — | `5f584eddf6553b63c46567ee9503ab26855aa2932de4937ca80e5f2cdf2e9ce4` |
| `00_REFERENCE_INTAKE/ASTROLABE Command Deck.dc.html` | 310,267 | `.html` | `png` | **yes** | `898dae2a9d66d9f2f225a7180b59a09022593ad38f8cfffe4d61ec4379109dd9` |
| `00_REFERENCE_INTAKE/ASTROLABE.dc.html` | 11,579,637 | `.html` | `mp4` | **yes** | `76a2ed782f76e978ef71b9e9f4fb6fb691c89f6d6bc6e4cdca015ec2e80ba46d` |
| `00_REFERENCE_INTAKE/AXIS-TITLES-PATCH.md` | 15,505 | `.md` | `text` | — | `2f28495273f129d15bee600432b3c594dc878b7c0f9b7152e7d8a1b9ce451c21` |
| `00_REFERENCE_INTAKE/Ai Result Comparision.docx` | 22,047 | `.docx` | `ooxml-word` | — | `cf973ce581fabbaf73e4b3a7fb790797fc9b5884886b23c4646f7f2e98483e28` |
| `00_REFERENCE_INTAKE/AlltheProjects - Detailed Metric Report.xlsx` | 7,113,127 | `.xlsx` | `ooxml-excel` | — | `8be962a01268e917714615b3bf1cc5e1a97bbea3da0317b8a450f7e0b1a36496` |
| `00_REFERENCE_INTAKE/AlltheProjects - Metric History Report.xlsx` | 832,579 | `.xlsx` | `ooxml-excel` | — | `aebb14fde4b2cdea7b81e8a712d4671523be6a1d4d052e2240dd4b59a93db2ca` |
| `00_REFERENCE_INTAKE/AlltheProjects - Quick Add Metrics .xlsx` | 289,844 | `.xlsx` | `ooxml-excel` | — | `f2a42b758fa845c9d969c8ed3772479ad9ac4ff64216959fc15906b85ed62fe8` |
| `00_REFERENCE_INTAKE/AlltheProjects Analysis Report - Quick Add Metrics.xlsx` | 17,135,711 | `.xlsx` | `ooxml-excel` | — | `27dd2b20d235d088b093157a71499e7e49af1772fceb0a15661047708ac92a05` |
| `00_REFERENCE_INTAKE/AlltheProjects.afw` | 13,691,894 | `.afw` | `gzip` | — | `ef93356e1bc762d8e14e05d65e797e60366cfccbaaea2be158fbbe261cb1bc91` |
| `00_REFERENCE_INTAKE/AlltheProjects.zip` | 9,721,934 | `.zip` | `zip` | — | `7d961a5e9eea903312233075766c5887e518ca95be09babee530a3e5820a1a87` |
| `00_REFERENCE_INTAKE/CLAUDE-CODE-HANDOFF.md` | 622,463 | `.md` | `png` | **yes** | `e872aa3eaa02bc8ee62f1d4c51badb92fb69570608e44ee17547df23a0bbe888` |
| `00_REFERENCE_INTAKE/CLAUDE.md` | 19,402 | `.md` | `text` | — | `0eaa90b0faf5e0f925fdd087761c6329c869a5a6bba4372a11efd7c68712c75a` |
| `00_REFERENCE_INTAKE/CRISPNESS-PATCH.md` | 15,284 | `.md` | `text` | — | `b6f06061546996c098a31b2218d45c135510fd34013ba1ad1ba1bbf8293ebf0c` |
| `00_REFERENCE_INTAKE/Concepts, Methods & Techniques-272662cf.docx` | 20,339 | `.docx` | `text` | **yes** | `9d8b8ad6248b7bc553ac2a15b319ddd5bea193e7fe826cee8a41518254d3d57c` |
| `00_REFERENCE_INTAKE/DEPOSIT-HERE.md` | 6,591 | `.md` | `text` | — | `f087989fcf210b7d81b7ae1f37248ce7a283dca371dcdfcceb31f56cff68725c` |
| `00_REFERENCE_INTAKE/DESIGN-GUIDE.md` | 752,246 | `.md` | `png` | **yes** | `1d4990ed7da7d4f0fcfba5700a8aed1382813b7660d8fc72530efc8bc0d71a56` |
| `00_REFERENCE_INTAKE/Executive Summary Large Test File.docx` | 25,269 | `.docx` | `ooxml-word` | — | `250cff6a9bb9afcffbed97a4e5d21dc3e8e9c51d6017e3519c4d857574044f11` |
| `00_REFERENCE_INTAKE/FILE-NAMES.md` | 3,724 | `.md` | `text` | — | `74f9c749991b1ee0d8bf768f8db84dc86058e72e6c0fa84f2e592399e7cdf5f2` |
| `00_REFERENCE_INTAKE/FX.afw` | 9,698,680 | `.afw` | `gzip` | — | `557bbd61d11656b8702a0a5b33cee8f5cbb7cc592baf7754972e2aae52b1a454` |
| `00_REFERENCE_INTAKE/GUIDED-MODE.md` | 19,863 | `.md` | `text` | — | `bd0d725fce7f48fd20b9c7428b414b9fa394ce99a586c4fa54b12fd161a9c222` |
| `00_REFERENCE_INTAKE/HANDOFF.md` | 24,107 | `.md` | `text` | — | `f0c4a7096f2413feb247ce2bb1d049a546f6db36ce308f0dfa1130dc4347b6b1` |
| `00_REFERENCE_INTAKE/Hard_File Forensic Analysis Report.xlsx` | 60,214 | `.xlsx` | `ooxml-excel` | — | `808ece07db72c4a6c7aff20c57d8dbbf83b2ce074461ab046c3d23835534489c` |
| `00_REFERENCE_INTAKE/INDEX.md` | 15,492 | `.md` | `text` | — | `61efe2cf52830f0b60b6e12e68c2bc9ba4ae4a81b5336801912a66b24b3425fd` |
| `00_REFERENCE_INTAKE/INT-02-Advanced-Schedule-Analysis.pdf` | 11,625,699 | `.pdf` | `pdf` | — | `859faf30473a3c062383c3b174fef9bc7b867b442b991ae75ff166a29485d855` |
| `00_REFERENCE_INTAKE/Large Test File (OverAl Fixed) UID_152_Directional_Path_Analysis_2026-6-24-13-17-48.xlsx` | 68,996 | `.xlsx` | `ooxml-excel` | — | `af12498ded27dba297863d8964d7bd21a78a17b80682a5f38aeb5eef803de54c` |
| `00_REFERENCE_INTAKE/Large_Test_File_UID_152_Directional_Path_Analysis_2026-7-8-8-45-50.xlsx` | 15,140 | `.xlsx` | `ooxml-excel` | — | `b67f02e49e5f94833eacd29203b41e9741c8492a50e00c4ab91b64d763d6d65e` |
| `00_REFERENCE_INTAKE/Mission Ops Redesign v2.dc (1).html` | 44,316 | `.html` | `ooxml-word` | **yes** | `272662cf43015e28d4db365c9425b3daebc9acc7ac9a4a8533fe67035795d34c` |
| `00_REFERENCE_INTAKE/Mission Ops Redesign v2.dc.html` | 1,068,787 | `.html` | `html` | — | `738120417fa5939dde29d4afc9d6c7b781d6c04dc5326023e72d017d7e3b8083` |
| `00_REFERENCE_INTAKE/Mission Ops Redesign.dc.html` | 159,063 | `.html` | `html` | — | `3c11a2f155a27b9e2af088e8bf6c1fd4a04ad7ec532d842f01603bb13b7f8c58` |
| `00_REFERENCE_INTAKE/NASA Metrics_Complete_20260423.aft` | 10,125,812 | `.aft` | `xml` | — | `7ab1c4aea22f4a1b3b83bd299c2c3f282efbf1db8d4407e9afecc69b6e945e14` |
| `00_REFERENCE_INTAKE/P-P5 - Quick Add Metrics .xlsx` | 25,916 | `.xlsx` | `ooxml-excel` | — | `e2c881f4890338c1817f01fe18d912c63c3b90aa80f1f0d3c3fa0361891b0ed7` |
| `00_REFERENCE_INTAKE/P2-P5 - DCMA Report.xlsx` | 603,625 | `.xlsx` | `ooxml-excel` | — | `9b9deed4365c5717eea09ae12ce9d896bdfc1beb868f8839365a7f08f0f3cb5c` |
| `00_REFERENCE_INTAKE/P2-P5 - Detailed Metric Report.xlsx` | 99,137 | `.xlsx` | `ooxml-excel` | — | `e9ecf008be4907a9c0a08829e8812551ebd9d9dbcb470291afef0a02bc362f9b` |
| `00_REFERENCE_INTAKE/P2-P5 - Metric History Report.xlsx` | 20,217 | `.xlsx` | `ooxml-excel` | — | `a67a98878323401b99059e67ede3dafa95fb6d6c67b368986bcd5d1bd544b46b` |
| `00_REFERENCE_INTAKE/P2-P5 - Quick Add Metrics.xlsx` | 172,439 | `.xlsx` | `ooxml-excel` | — | `4c4609d8dc64e717550653aef10dccf58fdaab76a4b0e875de4367543340e893` |
| `00_REFERENCE_INTAKE/PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx` | 848,020 | `.xlsx` | `ooxml-excel` | — | `14547256bf8c83b785a9f587c8c8436a311079fb89b44bf87088aa4ccab8fb3d` |
| `00_REFERENCE_INTAKE/PortfolioMap.dc.html` | 9,429 | `.html` | `html` | — | `7788a7f6fa792bb88ae256503627f9352c77197490b34b82a300abfe35a10cc0` |
| `00_REFERENCE_INTAKE/Project2 vs Project5_TAMPERED Forensic Analysis Report.xlsx` | 82,315 | `.xlsx` | `ooxml-excel` | — | `c0aebbc7d2868821d09471a10d7c84a566f6826acf43324f4552303f90bba19c` |
| `00_REFERENCE_INTAKE/Project2.mpp` | 691,712 | `.mpp` | `ole2-project` | — | `2fcdad6143ab5ddfac592cf6bda3798c7733a78e8332e3c73357e6145cdf1cfd` |
| `00_REFERENCE_INTAKE/Project2v5 Forensic Analysis Report.xlsx` | 81,318 | `.xlsx` | `ooxml-excel` | — | `c9646ab58c78b304f4132fcbe0a0ab958273d7be067aaf3cbd5503a6ddcc7e70` |
| `00_REFERENCE_INTAKE/Project5_TAMPERED.mpp` | 817,152 | `.mpp` | `ole2-project` | — | `f20d2fb2c2384441ca0490468373f353e4c18294e03fb911416d7a31a164bb28` |
| `00_REFERENCE_INTAKE/Project5_TAMPERED_UID_67_Directional_Path_Analysis_2026-7-8-8-19-10.xlsx` | 11,423 | `.xlsx` | `ooxml-excel` | — | `834e68133874ce73d67bf7d4edf58af5d54a03bf5136b8ed577981b9415210c3` |
| `00_REFERENCE_INTAKE/README (1).md` | 1,319 | `.md` | `text` | — | `29c383492c50a99399abfefa66cc8dc120a94c99b3a3ad9775e650ec6107ebc0` |
| `00_REFERENCE_INTAKE/README (2).md` | 21,413 | `.md` | `png` | **yes** | `48a7698844feb0326af085b1d8b6f03bfde5dd66bb98485f705754b9203c760a` |
| `00_REFERENCE_INTAKE/README.md` | 605,604 | `.md` | `png` | **yes** | `2bcb921f2a24bb7446ad7e0b4ae7b790c54aab5bdf2cb83b2a4bdc5ca0806a5e` |
| `00_REFERENCE_INTAKE/RENAME-PLAN.md` | 14,621 | `.md` | `text` | — | `1ddb6e2af36aee3667c2cad2d1fdcf9e6c0fcc4444a70e7a0c7a7e1b08c98d71` |
| `00_REFERENCE_INTAKE/Recording 2026-07-27 150631.mp4` | 44,316 | `.mp4` | `ooxml-word` | **yes** | `272662cf43015e28d4db365c9425b3daebc9acc7ac9a4a8533fe67035795d34c` |
| `00_REFERENCE_INTAKE/Redesign Explorations.dc.html` | 39,945 | `.html` | `html` | — | `9e3f71004e2e9214d322c712cf1549e7f379ede74f094d563a7b06e61beb8866` |
| `00_REFERENCE_INTAKE/SP-20240014019.pdf` | 14,471,540 | `.pdf` | `pdf` | — | `31360e10aa89bd28a6ebd02e1bb91fe9104fc6a25afb307b0b7d1025d712c775` |
| `00_REFERENCE_INTAKE/SP-20240014326.pdf` | 6,669,330 | `.pdf` | `pdf` | — | `4cd6b6d0afd1c0f21e1c4b3593319532ce1087522233be6036a484efae80aa11` |
| `00_REFERENCE_INTAKE/SRA - Large Test File2_SRA_Results_2026-8-6.xlsx` | 33,444 | `.xlsx` | `ooxml-excel` | — | `8059db102ebb58536eb9921befbfa21aa9bae4943d5076c8f3f0731f84a738fc` |
| `00_REFERENCE_INTAKE/SRA Large Test File2 POLARIS Output.jpg` | 100,771 | `.jpg` | `jpeg` | — | `972495066208bfb80487f8c08c033e7ca8a0c99f37c68b0f8eabd4f0c3cbf806` |
| `00_REFERENCE_INTAKE/SRA Large Test File2.mpp` | 9,443,328 | `.mpp` | `ole2-project` | — | `82522dcdfb0859211ffdfb2bb33319c61660e6ee69c3ae1249e612a1f5eeb751` |
| `00_REFERENCE_INTAKE/SRA Risk - Project5_TAMPERED - SRA.xlsx` | 17,442 | `.xlsx` | `ooxml-excel` | — | `bcc86d136d481d1f99e261aadfde754d0aef68f91a179b218840c34c7357360d` |
| `00_REFERENCE_INTAKE/SRA Sensitivity Analysis.xlsx` | 13,257 | `.xlsx` | `ooxml-excel` | — | `b77cc5ef833cfbc2bf0f0f59d6a58827e069e623bde989310310224d5f0eefaa` |
| `00_REFERENCE_INTAKE/Sensitivity - Large Test File2_SRA_Results_2026-8-6.xlsx` | 25,488 | `.xlsx` | `ooxml-excel` | — | `f02dc5e6d60b09e5b34c7ffc6d228cb1f395687774a71099573f7fbe467d6bee` |
| `00_REFERENCE_INTAKE/UI-INVENTORY.md` | 12,213 | `.md` | `text` | — | `6c4cb72391495841f458ecbfc592d266383531e03593548ec6b57b042e68738d` |
| `00_REFERENCE_INTAKE/UID_145_Directional_Path_Analysis_2026-6-22-11-35-10.xlsx` | 17,216 | `.xlsx` | `ooxml-excel` | — | `3c0e7c35b0aba8a6d7c1240210819529f45aeba7d10d9e3bc5758632bfdb80b7` |
| `00_REFERENCE_INTAKE/UID_145_Directional_Path_Analysis_2026-6-23-12-28-46.xlsx` | 11,110 | `.xlsx` | `ooxml-excel` | — | `c4a48fa436e9c3452cf4fbc70367d9962bf81bd16211f617229db643a05faba0` |
| `00_REFERENCE_INTAKE/UID_145_Directional_Path_Analysis_All_Dependencies_2026-6-23-12-37-10.xlsx` | 17,237 | `.xlsx` | `ooxml-excel` | — | `bdeb7a0b6fa6b5fc9cb408c935a877ffe7448407e2457f692931111ef6e342a9` |
| `00_REFERENCE_INTAKE/UID_152_Directional_Path_Analysis_2026-6-23-12-46-44.xlsx` | 68,885 | `.xlsx` | `ooxml-excel` | — | `b123dea3ea9c196f3681aececdc8e79bf9d73bc0dd2a4b5239e7fa7b80b39f6d` |
| `00_REFERENCE_INTAKE/UID_152_Directional_Path_Analysis_ALL_2026-6-23-15-5-21.xlsx` | 68,785 | `.xlsx` | `ooxml-excel` | — | `5d8e5654dc8876e600e58c352bbee8b84a8d659c9f5c3fa7f4e2a038c004ec6d` |
| `00_REFERENCE_INTAKE/UID_152_Directional_Path_Analysis_All Dependents Not Leveled_2026-6-23-20-30-55.xlsx` | 68,675 | `.xlsx` | `ooxml-excel` | — | `ab37c22425175a8cf001c00386b241be460d0b183d6bfeedb98b60e8b2da14d6` |
| `00_REFERENCE_INTAKE/UID_152_Directional_Path_Analysis_Leveled_All_Dependents_2026-6-23-20-28-26.xlsx` | 68,812 | `.xlsx` | `ooxml-excel` | — | `97de04ddb45c05e9d558a9bc472573cb02e8b5eade53128ced3b71bd4975ab57` |
| `00_REFERENCE_INTAKE/UID_152_Directional_Path_Analysis_Resource_Level_2026-6-23-17-8-43.xlsx` | 68,890 | `.xlsx` | `ooxml-excel` | — | `268d9f01dec32ec249c98466263bc37e2dcfa034fe5890cca5843bbb6d90e794` |
| `00_REFERENCE_INTAKE/UID_4_Directional_Path_Analysis_2026-6-23-15-42-46.xlsx` | 10,339 | `.xlsx` | `ooxml-excel` | — | `8bae99cf810bb5bbe47aaf1161fa70f9757210403028b79a85295509f7d82596` |
| `00_REFERENCE_INTAKE/UID_4_Directional_Path_Analysis_Progress_2026-6-23-16-0-6.xlsx` | 10,387 | `.xlsx` | `ooxml-excel` | — | `0dd1282533eba1085cec8bb9158a461e9860d16c00c451e26754d04e67c48a53` |
| `00_REFERENCE_INTAKE/UID_4_Directional_Path_Analysis_Split_2026-6-23-16-31-24.xlsx` | 10,387 | `.xlsx` | `ooxml-excel` | — | `13685f9cf58f9a960bde95523e81b637c6ce49496c8732c178331cd910390431` |
| `00_REFERENCE_INTAKE/Use Fable 5 Ultracode.md` | 699 | `.md` | `text` | — | `42e3137bd760e4080c6985c138e9f44153d88dddbbdd0100f19202e8bcb376f7` |
| `00_REFERENCE_INTAKE/VOICE-DECISION.md` | 23,245 | `.md` | `text` | — | `d25599708cd7b994055f3f470aed7d73b320e3098f89fa6cbd5ee7c592d8683f` |
| `00_REFERENCE_INTAKE/Workbook1 - DCMA Report.xlsx` | 1,113,854 | `.xlsx` | `ooxml-excel` | — | `d156d2700fe03279ad2f85a1d7484798e50f053fe701c96c5f86170a68dc81c9` |
| `00_REFERENCE_INTAKE/_ds_bundle.js` | 2,539 | `.js` | `text` | — | `e8b3b7e9a00865bdf50a0dd947ec4a4af036cd93c74096c9230bc9cf4f7379e9` |
| `00_REFERENCE_INTAKE/_ds_manifest.json` | 5,336 | `.json` | `text` | **yes** | `4a0a2b673c7eefbbd2f430619f8c09c5f89731d166459b8380a7cc6698f5dbd4` |
| `00_REFERENCE_INTAKE/a11y.js` | 3,050 | `.js` | `json` | **yes** | `d8bbddfd14511eb93d46173525937e8d446233b7618ac1e9c0fc1204b950dfba` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/.gitkeep` | 0 | `(none)` | `empty` | — | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HA296F~1.XLS` | 258,951 | `.xls` | `ooxml-excel` | **yes** | `edc37a87ca9670935829e4fe14faa9bd04da8bf8c80c465c0bcf2b2cf6818140` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HA3755~1.XLS` | 21,059 | `.xls` | `ooxml-excel` | **yes** | `088a4a3e9a05b077548a5e61f22435341863bb88a205d4b6f40400c392393688` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HA7B01~1.XLS` | 496,770 | `.xls` | `ooxml-excel` | **yes** | `7b863cbe28529b7dfee9967f6d9a850f0b0152af19ff6d76939492f3676bdc21` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HA88CE~1.XLS` | 90,187 | `.xls` | `ooxml-excel` | **yes** | `26e26bfa957c2076543083a011658e1a34d05458eee34763eb3c8e833d6988fb` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HA95A8~1.XLS` | 496,627 | `.xls` | `ooxml-excel` | **yes** | `3ab684888ac318ce47b92510705418d5a987c764ccb1dbfe635399f5fd29d314` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HARD_F~3.XLS` | 258,865 | `.xls` | `ooxml-excel` | **yes** | `52847764bd77319741a652f059c0be91e6f302d349547b2106e6fca2eaa3b66e` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/HARD_F~4.XLS` | 30,693 | `.xls` | `ooxml-excel` | **yes** | `3e612f369e7375c8f774ac357343e18d4ca04346e1ee315424190a993a30e0f3` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_Fuse - Fuse Analysis Report.xlsx` | 19,702 | `.xlsx` | `ooxml-excel` | — | `5a4c4d3c88905a8a8229a2f3f11787b01796b64317f15356e63ab811c5186cff` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_Fuse - Metric History Report.xlsx` | 20,284 | `.xlsx` | `ooxml-excel` | — | `57dc60eee7f805c751e764b3afaf92eae44f64fbfbf731d3b88e222f7c83282d` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_Fuse - Quick Add Metrics .xlsx` | 12,908 | `.xlsx` | `ooxml-excel` | — | `beec1ca535967185f795ab625dc11ad171d53e9d6d83b791f42d6fef038e160d` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_Fuse - Summary Metric Report.xlsx` | 463,274 | `.xlsx` | `ooxml-excel` | — | `be3d9e1de9ac12ec12d9c6ac76e10c41c3e8f2114d8a3e24efd25f25152d2475` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_Fuse.afw` | 549,799 | `.afw` | `gzip` | — | `f29b778bc44f00f774622b28431f1079cd27dfbbc17ff37b3cbcfbe436a93eaf` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_missing_logic.xlsx` | 10,227 | `.xlsx` | `ooxml-excel` | — | `fe88956c01ea607e7026d8debae292b40b5ec73f01df864d7b9c4c318650b426` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update vs update2_Fuse - Analysis Report.xlsx` | 24,277 | `.xlsx` | `ooxml-excel` | — | `0437c15d17214e567463ca6ccc20bb815767acd6269811d5282202f42511edc1` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update vs update2_Fuse - Detailed Metric Report.xlsx` | 90,889 | `.xlsx` | `ooxml-excel` | — | `b82425e3c294307db5a8fea35011293a2830a803e9aea8594d546e3a0f171e76` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update vs update2_Fuse - Excel .xlsx` | 23,658 | `.xlsx` | `ooxml-excel` | — | `e37a8a288e614e6ad7debdee715f098be61160347ceb29214944826055007225` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update vs update2_Fuse - Metric History Report.xlsx` | 21,750 | `.xlsx` | `ooxml-excel` | — | `8288f791c96334d97a32b0b692b3c2289dd785d1de6a9750fc7c9fe31d343bd8` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update vs update2_Fuse - Summary Report.xlsx` | 488,707 | `.xlsx` | `ooxml-excel` | — | `12acd0f190e9ad520d504f31bd1047610f0ae474929dee6506df0ac9830d2a22` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update vs update2_Fuse.afw` | 563,298 | `.afw` | `gzip` | — | `4d6a3b0faddd286b7af4303d928c18d2368903200ecef16ca1b36547412ab272` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update2 vs update3_Fuse - Analysis Report.xlsx` | 90,550 | `.xlsx` | `ooxml-excel` | — | `b9f55e48cffb2083029ca748735ef499f1551526e28acc18731325353019e46a` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update2 vs update3_Fuse - Detailed Metric Report.xlsx` | 91,312 | `.xlsx` | `ooxml-excel` | — | `f7fa1a55f6eedc9c5ed9a6ea105194b5e967afea04e4f3539d0e3ef1124adb81` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update2 vs update3_Fuse - Excel .xlsx` | 20,269 | `.xlsx` | `ooxml-excel` | — | `61349f33871f5e2d8c65c039c2ed560ef443c61c32fe63d7217e3ed01e3d39e1` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update2 vs update3_Fuse - Metric History Report.xlsx` | 20,617 | `.xlsx` | `ooxml-excel` | — | `c1f327934e58ee27ddd1a8e84cdaaa4f530063a7ef258209f307f792a1696f96` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update2 vs update3_Fuse - Metrics Report.xlsx` | 485,705 | `.xlsx` | `ooxml-excel` | — | `5b61e6c02128de8e9702bb426ffae8c95566e51575d1b15a53aa6845984de0b8` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update2 vs update3_Fuse - Summary Metrics Report.xlsx` | 485,660 | `.xlsx` | `ooxml-excel` | — | `c70401e516a2b78574a7a99d930a9a92155321e178c86bc71a871e2086bf8793` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_update2 vs update3_Fuse.afw` | 458,536 | `.afw` | `gzip` | — | `659bfac0e8e90cf5f858bb3a9384a1abe4f26e460ae5f1062ca453e5913c6eb6` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_updated vs update 2_ Forensic Analysis Report.xlsx` | 113,276 | `.xlsx` | `ooxml-excel` | — | `8c5d423806295a0c51db47868693649ab9ed4df30d321c76e6bb4be42960ef5e` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_updated2 vs update3 Forensic Analysis Report.xlsx` | 100,517 | `.xlsx` | `ooxml-excel` | — | `d98d557ad55cbfe6db6b4ec0729a31eae5abf31e37ff059209010e50769308db` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_updated3 vs Hard_File_updated4 24 hour calendar Acumen Fuse.afw` | 645,795 | `.afw` | `gzip` | — | `8cebe835d876445ac138851534e23e7c8d41c7019081517b03ca628c9a2da7b3` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_updated3 vs Hard_File_updated4 24 hour calendar Field Map.fieldmap.xml` | 19,357 | `.xml` | `xml` | — | `520baeb41d6bb6733355164199d254d7b6891580efdcdc02bc945c6d9f7a0506` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Hard_File_updated_missing_logic.xlsx` | 20,998 | `.xlsx` | `ooxml-excel` | — | `ac5cec0e540f846f138e187183a3cd74bdc31c518c3954ace595f1e21db9f65b` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File Acumen DCMA 14 Point vs Program Results.xlsx` | 257,090 | `.xlsx` | `ooxml-excel` | — | `96c26a435b8edf4d9c0aa177672bd416e145e246965e1c84650fcaa85b61fefa` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2 - Acumen Forensic Analysis Report.xlsx` | 499,462 | `.xlsx` | `ooxml-excel` | — | `ec036ebf98f566b00cb3b6d369932abb4e42a73b1fd4257edf0f3e530565dc82` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2 - Acumen Fuse - DCMA Report.xlsx` | 6,044,562 | `.xlsx` | `ooxml-excel` | — | `b3c6ef4ac880c95e99eb057939596022d78e3d6a2a2a9c965ffd2a00dd1e6e72` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2 - Acumen Fuse - Detailed Metric Report.xlsx` | 1,535,304 | `.xlsx` | `ooxml-excel` | — | `70343d4de1909cbe2dbab21baba7b9eb8ca152576b7b92152aa30ee3561fa347` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2 - Acumen Fuse -Metric History Report.xlsx` | 49,328 | `.xlsx` | `ooxml-excel` | — | `aeda4d952ced0cdba0192aa4ca8c5c2f05eb083e26c260b3de9811761edf8cb5` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2 - Acumen Fuse Analysis Quick Add Metrics.xlsx` | 279,641 | `.xlsx` | `ooxml-excel` | — | `583fa48537a1c870de1077fcf41c05d4aea6dc46658feba4ad49b710da156203` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2 - Acumen Fuse Quick Add Metrics .xlsx` | 28,124 | `.xlsx` | `ooxml-excel` | — | `891600833619662c978dde8902a1ba60620bf9ff869103bb6d56e3f941149a96` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2 - Acumen Fuse Summary Metric DCMA Report.xlsx` | 6,044,482 | `.xlsx` | `ooxml-excel` | — | `02d62d6cc9a822f222c27862a83c3f76a2cbcb07c37b300b6cd86b2b2afac199` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2 - Analyst Quick Add Metrics.xlsx` | 550,099 | `.xlsx` | `ooxml-excel` | — | `c4291551951fc0e2fdc9550d325528854a81eaedf301a817ad524af91b9fb4c5` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2 - Detailed Metric Report.xlsx` | 962,322 | `.xlsx` | `ooxml-excel` | — | `139ee874c29bd19f5994e6d60c645f61709aff6f4814d701e9164b8a19508f34` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2 - Executive Summary Quick Add Metrics.docx` | 24,167 | `.docx` | `ooxml-word` | — | `550cea748430e4c447735733e1665351669e003e3f09c5f4d850600559a3a4e8` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2 - MS Excel Quick Add Metrics .xlsx` | 18,980 | `.xlsx` | `ooxml-excel` | — | `9b7b9cd6d6d17d75827d8eab2dfb14820838bb08f2b554f9d1bbdf467e54b565` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2 Forensic Analysis Report.xlsx` | 1,013,159 | `.xlsx` | `ooxml-excel` | — | `c848a7b4ee2e911196c56b4bd6d4f57811da5d17ed5be3c5d5dac1ae618340af` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2.afw` | 3,191,886 | `.afw` | `gzip` | — | `cb4d2723f60585eddbb44a222b6dc68428bad7312dafa415a4d33c877e4cfd82` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File vs Large Test File2.fieldmap.xml` | 33,420 | `.xml` | `xml` | — | `da48a11340664c1f905635fd3d73ee4404082f4af94c7ef6a2e11ab810de9a9d` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File2 Acumen DCMA 14 Point vs Program Results.xlsx` | 264,709 | `.xlsx` | `ooxml-excel` | — | `9191d9ea168a3c3393b5cbdd8cd9059d65e0cc549703e8556d90ba53972da7f5` |
| `00_REFERENCE_INTAKE/acumen_v8.11.0/NASA Metrics_Complete_20260708.aft` | 9,860,096 | `.aft` | `xml` | — | `c296e6c206b52f4ccd9c4b3c648aef6cbf772a71c1588ff8550048e0c6f702f9` |
| `00_REFERENCE_INTAKE/advanced_sra.pdf` | 8,999 | `.pdf` | `text` | **yes** | `22a5207e7f8dca0304c6303d9173623f83f8e879a1ba44cd6ac2cb7dca43b82d` |
| `00_REFERENCE_INTAKE/advanced_sra.txt` | 54,180 | `.txt` | `html` | **yes** | `6d5befe849cd83720f30e850f4dcb68e12305568d1cda86f3e76d4d587bc4190` |
| `00_REFERENCE_INTAKE/ai_polish.js` | 75,012 | `.js` | `text` | — | `f16082c465eae91f185b83f807de6c858049c9f69cd6852aa4f4f69d469f9ce4` |
| `00_REFERENCE_INTAKE/app.css` | 31,659 | `.css` | `text` | — | `825df51f1a377f7ad3b51cb66ae697219549d42c7ee86ba98d7922a110f54b94` |
| `00_REFERENCE_INTAKE/app.js` | 5,287 | `.js` | `text` | — | `0b1e2e2afe3a49df8a795c80ecced54b1c58432e7f5d4e4abf5a3a54782b3a5a` |
| `00_REFERENCE_INTAKE/base.css` | 2,257 | `.css` | `text` | — | `345554533f3556f6d9b691b10814e848c6acccbdfe14ab6433839ac2374c9fa7` |
| `00_REFERENCE_INTAKE/beyond.png` | 51,013 | `.png` | `jpeg` | **yes** | `0b0363d5f20f7e69e09d0289b19fe43fd3ee042ed9ebe1a134bc72f2a523cdd0` |
| `00_REFERENCE_INTAKE/briefing.png` | 60,404 | `.png` | `jpeg` | **yes** | `3fc019608399c9606e8e97db1bd5b77439544e5f06de7e1afc30fb7f8ec861ea` |
| `00_REFERENCE_INTAKE/cei.js` | 1,818 | `.js` | `text` | — | `ebe1f3abbfcc897ccb9aa7c1657c7439c5997d928b71c4cc6bd47d99355cbc4e` |
| `00_REFERENCE_INTAKE/ch01-drill.png` | 51,503 | `.png` | `jpeg` | **yes** | `7b43c4bafc880113f43c6c54feaba7f5bd63b719d35987b8809e6ed42110c142` |
| `00_REFERENCE_INTAKE/chartframe.js` | 77,290 | `.js` | `text` | — | `12e6f04148237f31f5129f2103d34eaf0ab4907d2d12a6421c2690fb45e95e99` |
| `00_REFERENCE_INTAKE/checklist.js` | 50,872 | `.js` | `text` | — | `3c7a98d0da0fe980beb6ac09066ea46ad93ad7f4356c8a3a8e3b4b8d357192a5` |
| `00_REFERENCE_INTAKE/ci.yml` | 3,735 | `.yml` | `text` | — | `34f429903016ab0e08e6b27f05086de7906e245486706c6edc94d95567840252` |
| `00_REFERENCE_INTAKE/colresize.js` | 7,404 | `.js` | `text` | — | `a665eff7d7f5c12e1593574df95100d608b6a0f7bd6aa6d32b0695f0d1bafe17` |
| `00_REFERENCE_INTAKE/concepts_a.docx` | 11,625,699 | `.docx` | `pdf` | **yes** | `859faf30473a3c062383c3b174fef9bc7b867b442b991ae75ff166a29485d855` |
| `00_REFERENCE_INTAKE/concepts_a.txt` | 39,005 | `.txt` | `text` | — | `bf2fba156d553206bb984e7a6fc8d76034430290f64429ffb6be7a84d26ba8ae` |
| `00_REFERENCE_INTAKE/concepts_b.docx` | 4,863 | `.docx` | `json` | **yes** | `98414cd9834f6f5499465227150e6ef437fe0e37ce6416a46e3b70c79148a505` |
| `00_REFERENCE_INTAKE/concepts_b.txt` | 44,316 | `.txt` | `ooxml-word` | **yes** | `272662cf43015e28d4db365c9425b3daebc9acc7ac9a4a8533fe67035795d34c` |
| `00_REFERENCE_INTAKE/crispness-scan.json` | 34,965 | `.json` | `text` | **yes** | `153e2e6e573e729b4e3e328cd5e6babff6f6b4422904273b23575d8d4ad6636b` |
| `00_REFERENCE_INTAKE/ctl-check.png` | 36,001 | `.png` | `jpeg` | **yes** | `830da29c97132c7c9627679157d578f5b7ab98dc2f348fe7442bca74357a5b8a` |
| `00_REFERENCE_INTAKE/ctl-tiles.png` | 47,629 | `.png` | `jpeg` | **yes** | `6ea84c5e570d38cfb1fece3383548d1093ba35e5128186dd48bd622669794b48` |
| `00_REFERENCE_INTAKE/ctl-tiles2.png` | 47,629 | `.png` | `jpeg` | **yes** | `6ea84c5e570d38cfb1fece3383548d1093ba35e5128186dd48bd622669794b48` |
| `00_REFERENCE_INTAKE/curves.js` | 36,197 | `.js` | `text` | — | `59f6dab9118b53a030c2681c09cb3d39de755d5bf0d6da5a9f1af034976650a3` |
| `00_REFERENCE_INTAKE/dashboard.js` | 13,882 | `.js` | `text` | — | `e1a3a91b070501a81344a41075e56dbe18ef3329bdcc456134f53cb034bc0e12` |
| `00_REFERENCE_INTAKE/download` | 242,002 | `(none)` | `png` | — | `92af2bb133f6b1b5da6f995a4aa0f2b3888fb0f890372c50880f1f5bc189a16e` |
| `00_REFERENCE_INTAKE/draw-54db3784-3574-41e9-be5b-7d9249f2254c.png` | 806,741 | `.png` | `pdf` | **yes** | `1eafe822ff106f7fe6d11f7edb8cea2ebfc8f4ddb049d5488202e1375d9807f5` |
| `00_REFERENCE_INTAKE/draw-81bf283a-dbd7-4066-8596-672a9d3322a1.png` | 1,065,588 | `.png` | `html` | **yes** | `9edeb4793d834016cb6c90b159dfda8d75f030828c86ace36b62be1010b01ca0` |
| `00_REFERENCE_INTAKE/draw-b3e46260-3387-4693-85dc-8f3ed9a032db.png` | 3,923,990 | `.png` | `mp4` | **yes** | `317861011db5d27a30de622f5ad85e0c3295d729e54063c01fb04bc5c77d67ef` |
| `00_REFERENCE_INTAKE/drift.js` | 15,616 | `.js` | `text` | — | `8bcbd61b152ea8e326cdd88ca3245649a4dd5855acb76c96f08031c237756975` |
| `00_REFERENCE_INTAKE/drilldown.js` | 6,035 | `.js` | `text` | — | `3c7ef5a07e43171b6fb9d1d221b40b7ed30f079c008f9dc07c464b1a40da93ca` |
| `00_REFERENCE_INTAKE/driving_path.js` | 3,297 | `.js` | `text` | — | `db7552adc2ffe128c7e845ef4a36e56232cf3deada61c907488d802e7fa91d0c` |
| `00_REFERENCE_INTAKE/driving_tiers.js` | 21,428 | `.js` | `text` | — | `1aff079298a3562b21f23ed733a02a6d22bfe3c4a70fa6639fdcd085e4170f77` |
| `00_REFERENCE_INTAKE/elevation.css` | 4,907 | `.css` | `text` | — | `55d8c53917ada8057e4408fcb995a2bab8022d0e55f35c58a6bca79797d10ec1` |
| `00_REFERENCE_INTAKE/evmimplementationhandbook-1-1.pdf` | 3,215,471 | `.pdf` | `pdf` | — | `6f7da7e5e099d2497a1569156bfb2005884ca2f0dc9e80fefec6c3f64b37ff22` |
| `00_REFERENCE_INTAKE/favicon.ico` | 4,979 | `.ico` | `text` | **yes** | `7ecee81505889d361196ecaa275d03c60c7589627fc818166e9186582532dcfa` |
| `00_REFERENCE_INTAKE/findings_drill.js` | 9,639 | `.js` | `text` | — | `cdaa4606eb51c5f7b87d580f0db17cbd9134a4a69dca8795f7363b29415a000e` |
| `00_REFERENCE_INTAKE/forms.css` | 26,274 | `.css` | `json` | **yes** | `ddc3f8d3eccb909544ce010ac05d3ab5a830563fdcdfe77d0e660e5e9dc83077` |
| `00_REFERENCE_INTAKE/gantt.js` | 9,501 | `.js` | `text` | — | `0aefd731be4283d85d57f55e3bc622e216a5780871b551b675685efdc4a528af` |
| `00_REFERENCE_INTAKE/github.md` | 20,208 | `.md` | `riff` | **yes** | `e766224e24d38bb1f743c85f77e3055ece163a1f17c4cdfafeff5999f0a17b4b` |
| `00_REFERENCE_INTAKE/globe.js` | 12,286 | `.js` | `text` | — | `52199dd23f32ada71d939d1cdfecf4419aec3b14c0d62e4406a14a1f214ecaa9` |
| `00_REFERENCE_INTAKE/groups.js` | 8,982 | `.js` | `text` | — | `1031203c12399926ab3518d36e295573e88c0e902dea7f3978be19be4c91d6c0` |
| `00_REFERENCE_INTAKE/guide.png` | 48,794 | `.png` | `jpeg` | **yes** | `99e14757aeecb3a48eac4b8b1b9e3e132c067ab149212405fc419aba01c9983f` |
| `00_REFERENCE_INTAKE/heartbeat.js` | 8,800 | `.js` | `ico` | **yes** | `b807bc3201fd6e28a90f32a97922798b35a10e029903af8db73110b47d3c61ef` |
| `00_REFERENCE_INTAKE/hints.js` | 7,943 | `.js` | `text` | — | `27e960300c76aee8c7837730a08cc84e2e28007f402bf9ebb1b1b107a366ff20` |
| `00_REFERENCE_INTAKE/histogram.js` | 24,100 | `.js` | `text` | — | `7fcda4a8c3d8ceecb694f5b9330b97590675d5dc2dfa32861213e585775f0516` |
| `00_REFERENCE_INTAKE/home.js` | 12,557 | `.js` | `text` | — | `c3204703ddfdcd2d109e5f9ed19e74d1bf86b43a13731998d44beaa062095a99` |
| `00_REFERENCE_INTAKE/hud.css` | 3,474 | `.css` | `text` | — | `ea7084fb9adf18c1cfdba1c2e7f0495b293694cc7e23061e1706a980815faa3f` |
| `00_REFERENCE_INTAKE/i18n.py` | 972,120 | `.py` | `text` | — | `df6b01edfe98e6fe463f1d4f997f6d546b26aefa7d3e3f54bd7d6e5edc338433` |
| `00_REFERENCE_INTAKE/instruments-charts.css` | 206,281 | `.css` | `text` | — | `49949c8acfd36d96460abd91e1c24df2587afc8085437446e32903f0fafe025e` |
| `00_REFERENCE_INTAKE/instruments.css` | 48,479 | `.css` | `json` | **yes** | `4ff9aa9ff95871f308d803768a261b18e8baf32ab85b1c24e90d955c81b69b18` |
| `00_REFERENCE_INTAKE/int02_advanced.txt` | 44,316 | `.txt` | `ooxml-word` | **yes** | `272662cf43015e28d4db365c9425b3daebc9acc7ac9a4a8533fe67035795d34c` |
| `00_REFERENCE_INTAKE/integration-notes.md` | 488 | `.md` | `text` | — | `4a0f9dffc11156871d784de62258a43a14529dbee7481d1d55ae35cad2f2b468` |
| `00_REFERENCE_INTAKE/it-outline.png` | 46,484 | `.png` | `jpeg` | **yes** | `d3e1f5f33aadc162fadf8e88e25c339bda8a6a66b14c09be2b8576618cf232e9` |
| `00_REFERENCE_INTAKE/it-outline2.png` | 52,223 | `.png` | `jpeg` | **yes** | `527562c908a091b9a4599694cf40ef0d941460cc675efd1888304c7a00fa2d56` |
| `00_REFERENCE_INTAKE/legend_toggle.js` | 795 | `.js` | `text` | — | `13be4b18c26db168c105dcca3f1736c096c32ccfcc653234e0f27e9a7c70ae08` |
| `00_REFERENCE_INTAKE/margin.js` | 2,812 | `.js` | `text` | — | `4dc8266a0097021364086e3e5a3681ac96a25487950f3cd73041e3c5d143a30b` |
| `00_REFERENCE_INTAKE/margin_dashboard.js` | 11,481 | `.js` | `text` | — | `0b888cb49b5681997120a4a03edbc87cb5d39a9ea2f4d9548b261e5b0730aa01` |
| `00_REFERENCE_INTAKE/metric-lab-2.png` | 52,248 | `.png` | `jpeg` | **yes** | `ad575c08826c8a53a799a13bdca475f5ba70f5947e1f306154fb5e8090f1ac47` |
| `00_REFERENCE_INTAKE/metric-lab-3.png` | 57,728 | `.png` | `jpeg` | **yes** | `c3015fd6e03b3510cedcd906541c69ef6db16f62cd85e9e578a98ef203794b24` |
| `00_REFERENCE_INTAKE/metric-lab.png` | 57,623 | `.png` | `jpeg` | **yes** | `b386f4ec014d87e50b04227f2c3266ef29cb6be5abe758cb31eb995337616a68` |
| `00_REFERENCE_INTAKE/metrics_library/.gitkeep` | 0 | `(none)` | `empty` | — | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `00_REFERENCE_INTAKE/mission.js` | 4,121 | `.js` | `text` | — | `624cea97a6561cbee29bf6b74f55e5c505b20d8ea199899d9ab286489efe8c74` |
| `00_REFERENCE_INTAKE/mock-analysis.js` | 24,167 | `.js` | `jpeg` | **yes** | `32a4f50b19adb690afd660f766c623c538f66f43e6b83749f926f2b6eb3c8c83` |
| `00_REFERENCE_INTAKE/mock-api.js` | 35,937 | `.js` | `jpeg` | **yes** | `5d0b19a9da8261c5ed2bfca0881557a0028cbac6a333f9d6c4f949e776b065b2` |
| `00_REFERENCE_INTAKE/motion.css` | 5,795 | `.css` | `text` | — | `548dfc648228697465f0d62403bb901041a94cbc6b80e58b361a7a82784f8455` |
| `00_REFERENCE_INTAKE/mpp/.gitkeep` | 0 | `(none)` | `empty` | — | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `00_REFERENCE_INTAKE/mpp/24Hour Calendar.mpp` | 655,872 | `.mpp` | `ole2-project` | — | `88c8b673bfb3d41e6c8b0ef19dd0d3a49364b6b8179cb8d82d8e9c363a7a81f2` |
| `00_REFERENCE_INTAKE/mpp/FIXTURE-MANIFEST.json` | 3,777 | `.json` | `json` | — | `9421a2a287be0f93d4d4ce89b9333133b79c755e3569ccf173ada578a6cc55b2` |
| `00_REFERENCE_INTAKE/mpp/FX_Analysis_Report.xlsx` | 569,882 | `.xlsx` | `ooxml-excel` | — | `31db66f3e2d0d33b368b405e52aea7494a983f3bb32db1b37ff1ea49603ca3d4` |
| `00_REFERENCE_INTAKE/mpp/FX_Detailed_Metric_Report.xlsx` | 340,744 | `.xlsx` | `ooxml-excel` | — | `c20eda160c19c7930c51c2cf66489a2fbae6200388d103ede2be89ceb90cb1f7` |
| `00_REFERENCE_INTAKE/mpp/FX_Metric_History_Report.xlsx` | 766,709 | `.xlsx` | `ooxml-excel` | — | `9cbc4d9ac79a1e979357f3d78e2ecd85d9f868bcf7a7dafd4a210a7fb7a6294f` |
| `00_REFERENCE_INTAKE/mpp/Hard_File.mpp` | 1,295,360 | `.mpp` | `ole2-project` | — | `6a5fe4868499add6c8ccbc6e3bd8d3ced165b0cae9f64cf7aa2067891b7668bc` |
| `00_REFERENCE_INTAKE/mpp/Hard_File_updated.mpp` | 1,288,192 | `.mpp` | `ole2-project` | — | `cfd9a76304d113fc14b3899e64313374a821c5e3259a371d5284c17c67a4ea60` |
| `00_REFERENCE_INTAKE/mpp/Hard_File_updated2.mpp` | 1,468,928 | `.mpp` | `ole2-project` | — | `8921ca095f200c48d00cff673c5b70138113eed1451826f04c2d21ed31385b1a` |
| `00_REFERENCE_INTAKE/mpp/Hard_File_updated3.mpp` | 1,385,984 | `.mpp` | `ole2-project` | — | `dcd260832642cdca3877dffdcfd849328dde0e8507efbc51c87012f3ef62e6d8` |
| `00_REFERENCE_INTAKE/mpp/Hard_File_updated4 24 hour calendar.mpp` | 1,293,824 | `.mpp` | `ole2-project` | — | `fc2a9b2ae2daadcf7cfe1ac064b524cad72466b4bac4ca393ae9da51c915e504` |
| `00_REFERENCE_INTAKE/mpp/Hard_File_updated_with_logic_reestablished.mpp` | 1,243,136 | `.mpp` | `ole2-project` | — | `184bd57e5c9e87a133cf98b26dd468d39c1027fc9a96160d46e393e663dbb598` |
| `00_REFERENCE_INTAKE/mpp/Jacked Up Schedule 1.mpp` | 262,656 | `.mpp` | `ole2-project` | — | `bd10e2a5c08458956d98451b6e3561a77ce904e12bb9df333744ba7eeb650e30` |
| `00_REFERENCE_INTAKE/mpp/Jacked up Schedule 2.mpp` | 309,760 | `.mpp` | `ole2-project` | — | `b242999cb7776994e6eb2004b13503812bb16b7fae4847f31504764a4b913b82` |
| `00_REFERENCE_INTAKE/mpp/Large Test File Leveled.mpp` | 9,401,344 | `.mpp` | `ole2-project` | — | `b59a98360ff837a1e12454baddd1d74b2fc25c85840d7984a5c733a60e4accab` |
| `00_REFERENCE_INTAKE/mpp/Large Test File.mpp` | 9,262,592 | `.mpp` | `ole2-project` | — | `25a751248f1896b49c10464745af3f73bf833a58d79a2f1e9882d647d6e22cf1` |
| `00_REFERENCE_INTAKE/mpp/Large Test File2.mpp` | 9,463,808 | `.mpp` | `ole2-project` | — | `2a481131fc23f6ee1480186f49498c5f07634fff590a9cc08d6d874289ffe6c8` |
| `00_REFERENCE_INTAKE/mpp/Large_Test_File.mpp` | 9,713,664 | `.mpp` | `ole2-project` | — | `96ceb7d14d7a575cb42cda459c072edf6817d3a4eaa9e24a59a53bca2b62dae2` |
| `00_REFERENCE_INTAKE/mpp/Politte Schedule Tool.pptx` | 183,957 | `.pptx` | `ooxml-ppt` | — | `b848d56dcf908e53c4c0f534c3bfd6275e43484ec5e29d233b05ebfd79a5e564` |
| `00_REFERENCE_INTAKE/mpp/Project2.mpp` | 691,712 | `.mpp` | `ole2-project` | — | `2fcdad6143ab5ddfac592cf6bda3798c7733a78e8332e3c73357e6145cdf1cfd` |
| `00_REFERENCE_INTAKE/mpp/Project3.mpp` | 691,712 | `.mpp` | `ole2-project` | — | `66da8e7d58cb592b84b49b6245460c14a0122043ebce48654c0df289a16ab5bd` |
| `00_REFERENCE_INTAKE/mpp/Project4.mpp` | 692,224 | `.mpp` | `ole2-project` | — | `0348c097889898b939fbff7c02fa98cdab1548622c5ace0bc7fb3f94e2c02baf` |
| `00_REFERENCE_INTAKE/mpp/Project5.mpp` | 817,152 | `.mpp` | `ole2-project` | — | `0d1ab6f3b684143d5ca547afcd06f12ccbf3acab2fc9a0ee465a1a456252f818` |
| `00_REFERENCE_INTAKE/mpp/Project5_FX04_TamperDuration.mpp` | 626,176 | `.mpp` | `ole2-project` | — | `6d5d1d7188a6a532e3927eeb8cf45600b3e1e270e2d6924ae3c8cbcaa93bd9da` |
| `00_REFERENCE_INTAKE/mpp/Project5_FX04_TamperDuration.xml` | 750,236 | `.xml` | `xml` | — | `ff3331dadf95339b9de205ec978c53658870271634703ff6c68038b5695a5998` |
| `00_REFERENCE_INTAKE/mpp/Project5_FX05_TamperLogicDrop.mpp` | 626,176 | `.mpp` | `ole2-project` | — | `485d80dffedb1a42b75decc7e0b81a38b39da919e0216f6af6e5640d5fc99476` |
| `00_REFERENCE_INTAKE/mpp/Project5_FX05_TamperLogicDrop.xml` | 749,697 | `.xml` | `xml` | — | `6e91aba9523496a66d47bbdcce2f446ce44ea9fe13be0fd50d57482769cfea8d` |
| `00_REFERENCE_INTAKE/mpp/Project5_FX06_TamperBaselineShift.mpp` | 626,176 | `.mpp` | `ole2-project` | — | `1248d46a4fcdb361e62a5cec871e5b445fb717e521b0074048901230e6051810` |
| `00_REFERENCE_INTAKE/mpp/Project5_FX06_TamperBaselineShift.xml` | 750,237 | `.xml` | `xml` | — | `ccb599f77d91b683ac9dd5fe9d2877144531ab024b1f1802909336e51810014f` |
| `00_REFERENCE_INTAKE/mpp/Project5_TAMPERED.mpp` | 817,152 | `.mpp` | `ole2-project` | — | `0d1ab6f3b684143d5ca547afcd06f12ccbf3acab2fc9a0ee465a1a456252f818` |
| `00_REFERENCE_INTAKE/mpp/SRA Large Test File2.mpp` | 9,956,864 | `.mpp` | `ole2-project` | — | `6d7b0147a70b8faedcfdd2e82661483ec379f57cc283abe221342504862b77a8` |
| `00_REFERENCE_INTAKE/mpp/TP4_DataCenter_v3_FX01_MilestoneLate.mpp` | 355,328 | `.mpp` | `ole2-project` | — | `934d9037a379496ee7a125805404d2cdd00cac78243412c9bf7186e75cbd3238` |
| `00_REFERENCE_INTAKE/mpp/TP4_DataCenter_v3_FX01_MilestoneLate.xml` | 72,335 | `.xml` | `xml` | — | `0a79b4032ad591c3d283f80aa8ffc01360abf16e061a5606549709f491785852` |
| `00_REFERENCE_INTAKE/mpp/TP4_DataCenter_v3_FX02_EarlyFinish.mpp` | 303,616 | `.mpp` | `ole2-project` | — | `dd397d66ee9e7569ab5fc8e3ace1b504744965a11bad15ce2cd8a3beeaf06878` |
| `00_REFERENCE_INTAKE/mpp/TP4_DataCenter_v3_FX02_EarlyFinish.xml` | 72,286 | `.xml` | `xml` | — | `eacbec654e5efbdee603970f82d67f63ed8270d60ae8b320a231642fa8670363` |
| `00_REFERENCE_INTAKE/mpp/TP4_DataCenter_v3_FX03_DurationCut.mpp` | 303,616 | `.mpp` | `ole2-project` | — | `6c8fc436283fa9a3b63fb35b5df20e17540b6b7b6c9fcf26cd31bae86d00baab` |
| `00_REFERENCE_INTAKE/mpp/TP4_DataCenter_v3_FX03_DurationCut.xml` | 72,283 | `.xml` | `xml` | — | `9501b42bc1d78471595ed8fe4c8ffbc76082ca6b12495907e127443fd61146cf` |
| `00_REFERENCE_INTAKE/nasa-ibr-handbook-5-1.pdf` | 2,694,054 | `.pdf` | `pdf` | — | `fd1b310f4b4e3f45a982b627eac0faf06d240cbd063520c29406c794a039e7a9` |
| `00_REFERENCE_INTAKE/nasa-wbs-handbook.pdf` | 4,388,576 | `.pdf` | `pdf` | — | `90f63f49ed287c059c5fce37788ff11cda2dd005d0c806b3a5040b0b49126db7` |
| `00_REFERENCE_INTAKE/overlap.png` | 57,642 | `.png` | `jpeg` | **yes** | `42876758eb2395bdb60332591f644989bde9e42a469657bbefb2b67f64ac3a1e` |
| `00_REFERENCE_INTAKE/pasted-1783728087122-0.png` | 74,034 | `.png` | `png` | — | `853c8213f56508567b7661c86733b03e05376364f73c47f1f616b52136e7e702` |
| `00_REFERENCE_INTAKE/pasted-1783819903744-0.png` | 98,518 | `.png` | `png` | — | `a1ac9589f9c3ecb2762d3568ef9cd39a97a996237a5b5bca2b821668ca93a768` |
| `00_REFERENCE_INTAKE/pasted-1783820146085-0.png` | 95,738 | `.png` | `png` | — | `38e083922e3d2a8e93944f68ef260e00990f264358b6c78c47576d0a556b5e54` |
| `00_REFERENCE_INTAKE/pasted-1783822403853-0.png` | 99,274 | `.png` | `png` | — | `a1fb171501a6813613e566f2a2ee7259c7cd75df6454992b50a1c969574d30de` |
| `00_REFERENCE_INTAKE/pasted-1783878632522-0.png` | 297,110 | `.png` | `png` | — | `74f1877adce521ef41f750370316198ac35dfb98d8f3ff0496ff679965393d47` |
| `00_REFERENCE_INTAKE/pasted-1783880438707-0.png` | 144,580 | `.png` | `png` | — | `20c67b27194a3521af2f932f829ebbc66d7c9a25121e2541fc55e1ad1eace77f` |
| `00_REFERENCE_INTAKE/pasted-1783950199911-0.png` | 133,352 | `.png` | `png` | — | `d6a2d1a761bc8e7c492059154cf2fad1571b3c18a083a7d6dfe58807cc3aefac` |
| `00_REFERENCE_INTAKE/pasted-1783951970617-0.png` | 49,571 | `.png` | `png` | — | `7dbb906a85fe8f99b96c428709ff091f9610c2aeda11ad6f56d19b9a81ccb5da` |
| `00_REFERENCE_INTAKE/pasted-1783956881199-0.png` | 451,208 | `.png` | `png` | — | `18fdf0601d4714e90b3be59fe80add2f79276feead0990003243ae67615e6a36` |
| `00_REFERENCE_INTAKE/pasted-1783972694997-0.png` | 15,222 | `.png` | `png` | — | `3a11ad3375a93454b9913428ed6a1da21ceddb1aa25c129acec768ba0588724d` |
| `00_REFERENCE_INTAKE/pasted-1783972927581-0.png` | 14,426 | `.png` | `png` | — | `a2b4ceacbef9fb2cdbe762961d9642044437936d78c8610b8c0f656788f4be63` |
| `00_REFERENCE_INTAKE/pasted-1784934458029-0.png` | 297,261 | `.png` | `png` | — | `5c03494d2d95ea6a4893f824c7d285845bf92bd6f7f48b44a328006715364760` |
| `00_REFERENCE_INTAKE/pasted-1784934765307-0.png` | 294,417 | `.png` | `png` | — | `bc4b7871a03e17676a09dc56e1eb5088e2ee58f6281ad8f72473ee433e6b5a7f` |
| `00_REFERENCE_INTAKE/pasted-1785180481415-0.png` | 106,757 | `.png` | `png` | — | `1517f2c45eda4423f9564ce18209f261e554c07a3516ad03cb9f2afc551f74aa` |
| `00_REFERENCE_INTAKE/pasted-1785180498354-0.png` | 248,488 | `.png` | `png` | — | `f371133a33d873ca19719520d74262d45f76a2e8e9d8e880becbc0cbde9cdc0a` |
| `00_REFERENCE_INTAKE/pasted-1785180513147-0.png` | 79,226 | `.png` | `png` | — | `b5413b58c24bddd576027f01d581e52a80933a65b45b2158ae55a040400f9ff1` |
| `00_REFERENCE_INTAKE/path.js` | 12,180 | `.js` | `text` | — | `1260fbd6254fd679b42c06a40425e7f5759e2fa4f68cb70db79974bd3c3538e9` |
| `00_REFERENCE_INTAKE/path_evolution.js` | 6,225 | `.js` | `text` | — | `cd780b1e1801e6e2a68a73409f6426ab82cdd47c7456ba18d6f1d9d003cfe59c` |
| `00_REFERENCE_INTAKE/pbix/.gitkeep` | 0 | `(none)` | `empty` | — | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `00_REFERENCE_INTAKE/pbix/NSATDeploymentRevisionAlpha.pbix` | 14,534,820 | `.pbix` | `zip` | — | `27ebb3d231a66c111d56fda7940d28a240cee9208c9621563678031a3dddd1f7` |
| `00_REFERENCE_INTAKE/performance.js` | 11,613 | `.js` | `text` | — | `ac3dce335fd39ae4bb43e50963c40942043b3a6e18a956245c058abb7c550dfa` |
| `00_REFERENCE_INTAKE/persist.js` | 24,307 | `.js` | `text` | — | `344fb360a971aa44f38023f7128f9a4367bbfbb20a000b97bbfb8a77254b9403` |
| `00_REFERENCE_INTAKE/pm-handbook-nasa-sp-2014-3705-2024jun.pdf` | 11,248,846 | `.pdf` | `pdf` | — | `42c68ad040389875aabc9cb92a4155337f9c58d1571feb684c0c037022fd6e61` |
| `00_REFERENCE_INTAKE/ppc-handbook-1-5-17.pdf` | 4,581,125 | `.pdf` | `pdf` | — | `d36d9776cb1b2b4520b4dac449ad425d3ec3ebe7ffaa36054e5cf1d5dc7f3438` |
| `00_REFERENCE_INTAKE/probe-analysis.html` | 38,325 | `.html` | `text` | **yes** | `808fc682b1f8d87af901197b457d19823fe9737d80908dd14a6729dbe4bcd843` |
| `00_REFERENCE_INTAKE/reel-f0.png` | 11,398 | `.png` | `json` | **yes** | `2c4bb563b1150ab6d81e2ac297fe0d5ee3a8394f48acf593814036b3877385e6` |
| `00_REFERENCE_INTAKE/reel-f1.png` | 27,691 | `.png` | `text` | **yes** | `f39ca79076ee5488396bdfedc18a0c2f4ba899f4acde7fb237da7449df21b964` |
| `00_REFERENCE_INTAKE/reel-f2.png` | 41,751 | `.png` | `json` | **yes** | `f02d1645cdb20a89ac28057061e08ae5ae80220a323b34bf176cb78a6bad0f66` |
| `00_REFERENCE_INTAKE/reel-f4.png` | 576,282 | `.png` | `png` | — | `2ac018b2521fba4e0d016f1d23c31d3a6dba36cd95b8c316fd2a0d9df3460f62` |
| `00_REFERENCE_INTAKE/reel_shot-1785179231876.mp4` | 267,519 | `.mp4` | `png` | **yes** | `9ed1e74ed206966b95fbad52807e12b4bc476fcb7b092d0f87ccc0723285efd6` |
| `00_REFERENCE_INTAKE/references/.gitkeep` | 0 | `(none)` | `empty` | — | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `00_REFERENCE_INTAKE/references/106 Advanced Schedule RiskPresentation Lisbon.ppt` | 878,592 | `.ppt` | `ole2-ppt` | — | `14ab24a183417dc3988338612c9ddf41bd603cb719b7665fa24dec8a77dfb84b` |
| `00_REFERENCE_INTAKE/references/CLAUDE CODE NEXT PROMPT FOR THURSDAY 07162026.docx` | 94,850 | `.docx` | `ooxml-word` | — | `58c180d2a936597665f6f6724abfd92812fdf1694755ae950d57a5efb961ee0e` |
| `00_REFERENCE_INTAKE/references/ChatGPT Repository Audit  07152026.docx` | 24,298 | `.docx` | `ooxml-word` | — | `31b578aa2c2f6359beba0da6ad4514f0d0c89d0eae38edb64496342a8ef453a9` |
| `00_REFERENCE_INTAKE/references/Concepts, Methods & Techniques.docx` | 44,316 | `.docx` | `ooxml-word` | — | `272662cf43015e28d4db365c9425b3daebc9acc7ac9a4a8533fe67035795d34c` |
| `00_REFERENCE_INTAKE/references/Field Map.fieldmap.xml` | 12,630 | `.xml` | `xml` | — | `e9cff89caab9b24347694a322e7c8656d57af13d926dbc1b3b4e8fef3694485c` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_AND_ORACLE_TEST_PROTOCOL.docx` | 49,063 | `.docx` | `ooxml-word` | — | `579486fb3c1a398d5d685f9c6ef4dc96b5330bd4dfd15968d25394df8a8f40c9` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_AND_ORACLE_TEST_PROTOCOL.md` | 25,819 | `.md` | `text` | — | `67f7a9e411ae2878ae1542af2861cdb197923d2753ec95d22557d6e20dffc9e3` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V10_BUNDLE/HARDENED_ASSOCIATIONS_V10.csv` | 78,255 | `.csv` | `text` | — | `11dfcaf2a548208c101944efdc56b30dd7c846347fc495b5e48032e88cfc0efa` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V10_BUNDLE/HARDENED_AUDIT_V10_BUNDLE.zip` | 4,280,316 | `.zip` | `zip` | — | `19415cfd3fa191a41bba0834e8c633be4ae559a7278cb85bcc0c6f6f3d4cdded` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V10_BUNDLE/HARDENED_BIDIRECTIONAL_INDEX_V10.csv` | 256,046 | `.csv` | `text` | — | `5edc9eb401dd492a19eee76d5aa1d64c4a9dba5b83ec937f92bf39677be81573` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V10_BUNDLE/HARDENED_CROSS_REFERENCE_V10.xlsx` | 463,484 | `.xlsx` | `ooxml-excel` | — | `4a276904e764bea6836cebb689adbdcbacc7dcae6302e0a06cc956013c9f4ace` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V10_BUNDLE/HARDENED_CROSS_REFERENCE_V10_preview.png` | 173,053 | `.png` | `png` | — | `362546c44d07da37a063a2d0b2b42f4c4c2371b829201400c5853cb7b6413a59` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V10_BUNDLE/HARDENED_FILE_REVERSE_INDEX_V10.csv` | 21,849 | `.csv` | `text` | — | `2dd7ee5da712a0f750b94fe7a13525394b8600dc6350c7a88ef62373ab0e0964` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/FILE_RENAME_AND_DISPOSITION_VERIFIED.xlsx` | 107,521 | `.xlsx` | `ooxml-excel` | — | `8a87bb4e42b586ee7bb329d1252cae652dc8d7e295642fd9f1ab59875d6ba3ac` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/FILE_RENAME_MAP_VERIFIED.csv` | 82,135 | `.csv` | `text` | — | `8e4128c124d6e1fcbbf19cb4d5dd0db0d0310f1cdea31477ef7df5b31c8b0c84` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/HARDENED_ASSOCIATIONS_V5.csv` | 67,847 | `.csv` | `text` | — | `d6917b3d98e50def88cba90259d65e324e013e61d5d60a1b9058ee3cb84e2376` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/HARDENED_ASSOCIATIONS_V5.json` | 125,584 | `.json` | `json` | — | `74e631d3986190fc6a6afefe0c544410d7c214860cba7c3863238978924b5d4c` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/HARDENED_AUDIT_AND_ORACLE_TEST_PROTOCOL.docx` | 49,063 | `.docx` | `ooxml-word` | — | `579486fb3c1a398d5d685f9c6ef4dc96b5330bd4dfd15968d25394df8a8f40c9` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/HARDENED_AUDIT_AND_ORACLE_TEST_PROTOCOL.md` | 25,819 | `.md` | `text` | — | `67f7a9e411ae2878ae1542af2861cdb197923d2753ec95d22557d6e20dffc9e3` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/HARDENED_AUDIT_AND_ORACLE_TEST_PROTOCOL.pdf` | 251,267 | `.pdf` | `pdf` | — | `d5402eb1ff9913c8e4f0a3ccc56196ed2dca7ee9fea248ef6df08f5785b9bfb7` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/HARDENED_AUDIT_V9_BUNDLE.zip` | 4,263,807 | `.zip` | `zip` | — | `89909ee82b6c6e5f61d75a59e71c4bf302025de9d90b1713e1968d7be9c1946f` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/HARDENED_CORPUS_CROSS_REFERENCE.xlsx` | 124,790 | `.xlsx` | `ooxml-excel` | — | `2cbe6825e36abcbdc3452f621e1deb74b5a7c7f3282c9ed44395b396a570e698` |
| `00_REFERENCE_INTAKE/references/HARDENED_AUDIT_V9_BUNDLE/hardened_audit.py` | 43,866 | `.py` | `text` | — | `3d017d2152df128f2d999fdb869bea723824fcd6318e3e564c7f703e005aa656` |
| `00_REFERENCE_INTAKE/references/HARDENED_CORPUS_CROSS_REFERENCE.xlsx` | 124,790 | `.xlsx` | `ooxml-excel` | — | `2cbe6825e36abcbdc3452f621e1deb74b5a7c7f3282c9ed44395b396a570e698` |
| `00_REFERENCE_INTAKE/references/INT-02-Advanced-Schedule-Analysis.pdf` | 806,741 | `.pdf` | `pdf` | — | `1eafe822ff106f7fe6d11f7edb8cea2ebfc8f4ddb049d5488202e1375d9807f5` |
| `00_REFERENCE_INTAKE/references/POLARIS_Delta_Audit_2026-07-15.md` | 6,579 | `.md` | `text` | — | `1eacb4a3a3fefeca9e9c62d1f90bc6b51034ebca51c933b5d61f333b2752f12f` |
| `00_REFERENCE_INTAKE/references/POLARIS_Independent_Audit_2026-07-15.md` | 14,043 | `.md` | `text` | — | `ef87fba7ca9e0db92373f831d8bbe23d0cee6c05ec77799cca2ccad1d1ec03d2` |
| `00_REFERENCE_INTAKE/references/POLARIS_Reference_Corpus_Delta_2026-07-15.json` | 50,112 | `.json` | `json` | — | `16ccd682747a363f9ae69d31d1ae0137c506061d4f841c9470da655954589564` |
| `00_REFERENCE_INTAKE/references/PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx` | 848,020 | `.xlsx` | `ooxml-excel` | — | `14547256bf8c83b785a9f587c8c8436a311079fb89b44bf87088aa4ccab8fb3d` |
| `00_REFERENCE_INTAKE/references/SP-20240014019.pdf` | 14,471,540 | `.pdf` | `pdf` | — | `31360e10aa89bd28a6ebd02e1bb91fe9104fc6a25afb307b0b7d1025d712c775` |
| `00_REFERENCE_INTAKE/references/SP-20240014326.pdf` | 6,669,330 | `.pdf` | `pdf` | — | `4cd6b6d0afd1c0f21e1c4b3593319532ce1087522233be6036a484efae80aa11` |
| `00_REFERENCE_INTAKE/references/TP1_Library_Progressed.xml` | 35,608 | `.xml` | `xml` | — | `43470d9f8232549d53720256f27a2e38c967cabd055c17b800cb6be14c99182c` |
| `00_REFERENCE_INTAKE/references/TP2_Bridge_4x10_Calendar.xml` | 26,503 | `.xml` | `xml` | — | `8e6116bab150d6316f90dc0f0f3ecdb7a330a5a76fe3a61aaee3a1039a05ae48` |
| `00_REFERENCE_INTAKE/references/TP3_Outage_DCMA_Seeded.xml` | 32,802 | `.xml` | `xml` | — | `f29b7ef5a4d52ed771b8178d04e3d432322a0b87e45945711a61b455de6b911b` |
| `00_REFERENCE_INTAKE/references/TP4_DataCenter_v1.xml` | 22,199 | `.xml` | `xml` | — | `b3f06cbde6ca9c3c280f729e10fba261d351b659187527304cbc41dab2804b26` |
| `00_REFERENCE_INTAKE/references/TP4_DataCenter_v2.xml` | 22,748 | `.xml` | `xml` | — | `1fba86961cd91eb0dc059e5dee7645be5ca57704ac61be5f0cccf492f3e608c1` |
| `00_REFERENCE_INTAKE/references/TP4_DataCenter_v3.xml` | 22,966 | `.xml` | `xml` | — | `55102caa93dd9c66738f795e9d0dada4514fa5ef1e5c0bdd46636b1362f2fbe9` |
| `00_REFERENCE_INTAKE/references/TP4_DataCenter_v4.xml` | 23,296 | `.xml` | `xml` | — | `14b380d03d0348ada9ca4a674658dae4ca3a625b2473047fd203d970f5af5d89` |
| `00_REFERENCE_INTAKE/references/TP4_DataCenter_v5.xml` | 23,404 | `.xml` | `xml` | — | `8625f98841cc37f6eef57c50633bfd98d2fdafe62de653d3898d897eaaf011da` |
| `00_REFERENCE_INTAKE/references/evmimplementationhandbook-1-1.pdf` | 3,215,471 | `.pdf` | `pdf` | — | `6f7da7e5e099d2497a1569156bfb2005884ca2f0dc9e80fefec6c3f64b37ff22` |
| `00_REFERENCE_INTAKE/references/nasa-ibr-handbook-5-1.pdf` | 2,694,054 | `.pdf` | `pdf` | — | `fd1b310f4b4e3f45a982b627eac0faf06d240cbd063520c29406c794a039e7a9` |
| `00_REFERENCE_INTAKE/references/nasa-wbs-handbook.pdf` | 4,388,576 | `.pdf` | `pdf` | — | `90f63f49ed287c059c5fce37788ff11cda2dd005d0c806b3a5040b0b49126db7` |
| `00_REFERENCE_INTAKE/references/pm-handbook-nasa-sp-2014-3705-2024jun.pdf` | 11,248,846 | `.pdf` | `pdf` | — | `42c68ad040389875aabc9cb92a4155337f9c58d1571feb684c0c037022fd6e61` |
| `00_REFERENCE_INTAKE/references/ppc-handbook-1-5-17.pdf` | 4,581,125 | `.pdf` | `pdf` | — | `d36d9776cb1b2b4520b4dac449ad425d3ec3ebe7ffaa36054e5cf1d5dc7f3438` |
| `00_REFERENCE_INTAKE/references/reference_manifest.json` | 100,636 | `.json` | `json` | — | `4d1948d91b8bc785a51b135ea5cf1f3a91611f2cd75fa21288ef211f7df2c085` |
| `00_REFERENCE_INTAKE/references/reference_structural_summary.json` | 177,726 | `.json` | `json` | — | `0c93c0e7a54ac734f7bc0ccd339a1abe88966e985bfc71d430381b63ec165648` |
| `00_REFERENCE_INTAKE/references/schedule-management-handbook-20240315-update.zip` | 24,454,850 | `.zip` | `zip` | — | `48f7294a3c6d279d444a6639edaed49293cc4d70838cac96daf4f94184129696` |
| `00_REFERENCE_INTAKE/references/smp-template-20200225.docx` | 44,826 | `.docx` | `ooxml-word` | — | `b522a173071325ba189fe822b30e6e4607f7a9cf5608a8672052a73773add7ba` |
| `00_REFERENCE_INTAKE/references/sopi_6.0_final.pdf` | 1,421,384 | `.pdf` | `pdf` | — | `b9105a99df970143456239f94bf88ab81e8f1255675baf2417be681b2ba57f9a` |
| `00_REFERENCE_INTAKE/references/sra-ssi-setup.json` | 46,285 | `.json` | `json` | — | `0a7701cbe02a3411e60d631c2a2ce2567f2e6fa44db90798de469df8bb56dcd6` |
| `00_REFERENCE_INTAKE/references/srb-handbook-official-rev-c-202301243-final-v2.pdf` | 1,193,319 | `.pdf` | `pdf` | — | `73c0a47635465b31be964a532be1ae150be982e9f5263fa188061d1fc046608f` |
| `00_REFERENCE_INTAKE/repo-audit.json` | 34,965 | `.json` | `text` | **yes** | `153e2e6e573e729b4e3e328cd5e6babff6f6b4422904273b23575d8d4ad6636b` |
| `00_REFERENCE_INTAKE/repo-audit.md` | 10,821 | `.md` | `text` | — | `8b614f2ccb4f6e98732d4a05d4e66e23c5ca576abaefa2ecd969ca49606f4330` |
| `00_REFERENCE_INTAKE/resources.js` | 3,966 | `.js` | `text` | — | `7e8e65e086360def7cacb50adf76b189d875ee252631bf9d6396b319976972b3` |
| `00_REFERENCE_INTAKE/ribbon_drill.js` | 35,729 | `.js` | `text` | — | `8d65d0d8bc6458ba1a8f1c2db7cfde31414770411971984dd56ff44f2757865c` |
| `00_REFERENCE_INTAKE/scatter.js` | 23,538 | `.js` | `text` | — | `67619e91a2428018a151392a338a36eded1d9cb8e149d6136d1a237f64d59692` |
| `00_REFERENCE_INTAKE/schedule-forensics-read-only-audit-evidence.zip` | 388,243 | `.zip` | `zip` | — | `440ef4535ebe7188f38aa60258dbe1d9d362c726e48732779af607a5f9b1edea` |
| `00_REFERENCE_INTAKE/schedule-management-handbook-20240315-update.zip` | 24,454,850 | `.zip` | `zip` | — | `48f7294a3c6d279d444a6639edaed49293cc4d70838cac96daf4f94184129696` |
| `00_REFERENCE_INTAKE/scorecards.js` | 28,660 | `.js` | `text` | — | `3251af8867579035501390066fd60a17189acbe6629529af471c942f2f1e7581` |
| `00_REFERENCE_INTAKE/scurve.js` | 10,142 | `.js` | `text` | — | `d18b1287899f2bda84b61d86eb2fd2fdbd68c4dede4648206ad3be6bfe693f4d` |
| `00_REFERENCE_INTAKE/seg-forecast-2.png` | 48,868 | `.png` | `jpeg` | **yes** | `27190b4563646bdca5533a1355a21fc4ad272fec3031fd4c9d93369cbd225c1f` |
| `00_REFERENCE_INTAKE/seg-forecast.png` | 61,546 | `.png` | `jpeg` | **yes** | `28c045d356b084a2511fc76836f8565534e5a6a4e5530cb4f6b421db2769a566` |
| `00_REFERENCE_INTAKE/settings.js` | 10,888 | `.js` | `text` | — | `5a1b884608cf0899c17aceb7d365003c108b1a862575f035e524185a0e3237c6` |
| `00_REFERENCE_INTAKE/sf-themes.css` | 438,326 | `.css` | `png` | **yes** | `01937250b32df6b787ec66a667e07dae3ce750db777e60c194532b28a1716ec9` |
| `00_REFERENCE_INTAKE/sopi_6.0_final.pdf` | 1,421,384 | `.pdf` | `pdf` | — | `b9105a99df970143456239f94bf88ab81e8f1255675baf2417be681b2ba57f9a` |
| `00_REFERENCE_INTAKE/spacing.css` | 3,951 | `.css` | `text` | — | `067475edccbdda31872d12648af41d101097a04a45f5e4924e581cb1d203dc6a` |
| `00_REFERENCE_INTAKE/sra-report January 2026.docx` | 9,589 | `.docx` | `ooxml-word` | — | `822b17053f23b57023cbeb1b73e46b25a5e63378eaa6eb841f075501fe76f85b` |
| `00_REFERENCE_INTAKE/sra-report.docx` | 30,045 | `.docx` | `ooxml-word` | — | `f07bddab86cc90fb25a48f143da968e8b8a3e00c34af50244bff612d8f911948` |
| `00_REFERENCE_INTAKE/sra-ssi (January 2026).xlsx` | 6,499 | `.xlsx` | `ooxml-excel` | — | `601acf54af1dd9b3f6f9b1e52a1aa7c5c12c991e7a9d7e078a40fdd9ae7fe6ba` |
| `00_REFERENCE_INTAKE/sra-ssi.xlsx` | 17,054 | `.xlsx` | `ooxml-excel` | — | `b05c62921daa901eecb33de885a32a0e104e143cbc219e225fa53b862b31c223` |
| `00_REFERENCE_INTAKE/sra.js` | 8,848 | `.js` | `text` | — | `9ef7ed27f77a5fe7d3402be4210872f33261143ee7da13f35f414fbddcc909e3` |
| `00_REFERENCE_INTAKE/sra_grid.js` | 7,533 | `.js` | `text` | — | `283366b95381b38de7eaff831c27eeba059293843d3b7bd88a38b5ad22d7608e` |
| `00_REFERENCE_INTAKE/sra_jcl.js` | 4,001 | `.js` | `text` | — | `f9c5d6d6a14526591de1bb36e2683f0cbc24e75315d6c734e62b5743f73530cb` |
| `00_REFERENCE_INTAKE/sra_risk.js` | 15,723 | `.js` | `text` | — | `4fc1b4dac5a4b75f56dfddd8ba263bfec6ec655748f9bc990d98c0f4227cfff8` |
| `00_REFERENCE_INTAKE/srb-handbook-official-rev-c-202301243-final-v2.pdf` | 1,193,319 | `.pdf` | `pdf` | — | `73c0a47635465b31be964a532be1ae150be982e9f5263fa188061d1fc046608f` |
| `00_REFERENCE_INTAKE/ssi/.gitkeep` | 0 | `(none)` | `empty` | — | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `00_REFERENCE_INTAKE/ssi/Hard File updated3_UID_155_Directional_Path_Analysis_2026-7-15.xlsx` | 16,791 | `.xlsx` | `ooxml-excel` | — | `4bfe2ce3a66085101e544af7b12f39fa0850dd84b406e69c0ece9062688d6a17` |
| `00_REFERENCE_INTAKE/ssi/Hard_File_Path_Trace_UID_155_Directional_Path_Analysis_2026-7-8-13-30-7.xlsx` | 16,021 | `.xlsx` | `ooxml-excel` | — | `a585df8219192ee059151f93eb2f4e953ab8fda80ed9955e84e1c49eb86bcc38` |
| `00_REFERENCE_INTAKE/ssi/Hard_File_Path_Updated_Trace_UID_155_Directional_Path_Analysis_2026-7-8-13-30-7.xlsx` | 15,801 | `.xlsx` | `ooxml-excel` | — | `d6c5e48351b481be0de48a5fdf8d66e22d474aae5a0806ded580146f71ae9d86` |
| `00_REFERENCE_INTAKE/ssi/Hard_File_updated4 24 hour calendar_UID_155_Directional_Path_Analysis 2026-7-15.xlsx` | 16,720 | `.xlsx` | `ooxml-excel` | — | `c8680045cc0b94fbfc62bc4a86824a2045b9eb00dc65b437e0ef40b022535478` |
| `00_REFERENCE_INTAKE/ssi/Large Test File Leveled 152_Directional_Path_Analysis_2026-7-14 (b).xlsx` | 19,088 | `.xlsx` | `ooxml-excel` | — | `bdc74b4a276c7de10d77753c7bcf777050885d2c2cc68777bf9d5087e2bb0b6a` |
| `00_REFERENCE_INTAKE/ssi/Large Test File Leveled UID_152_Directional_Path_Analysis_2026-7-14.jpg` | 80,126 | `.jpg` | `jpeg` | — | `211fe51989b8efd549ba4d382c3b694a11fbcc5839cc6052fdf261970c370bfb` |
| `00_REFERENCE_INTAKE/ssi/Large Test File Leveled UID_152_Directional_Path_Analysis_2026-7-14.xlsx` | 68,081 | `.xlsx` | `ooxml-excel` | — | `8da48082abc198fa3da70749a9c91abd8b762e3fc80bc08b1fa4c482c021b9d3` |
| `00_REFERENCE_INTAKE/ssi/Large Test File UID_152_Directional_Path_Analysis_All_Dependicies_SSI_2026-7-15.xlsx` | 64,052 | `.xlsx` | `ooxml-excel` | — | `db0831069022b9aed79e447dad00dc6120026478c120f49dc28b96d100535a83` |
| `00_REFERENCE_INTAKE/ssi/Large Test File2 UID_152_Directional_Path_Analysis_All_Dependicies_SSI_2026-7-15.xlsx` | 68,096 | `.xlsx` | `ooxml-excel` | — | `2c2c2fd9ad570dcc34cd5139b90c97a39ce023e9136d8c41fc918b252fc0120e` |
| `00_REFERENCE_INTAKE/ssi/Large_Test_File_UID_152_Directional_Path_Analysis_2026-7-8-8-45-50.xlsx` | 15,140 | `.xlsx` | `ooxml-excel` | — | `b67f02e49e5f94833eacd29203b41e9741c8492a50e00c4ab91b64d763d6d65e` |
| `00_REFERENCE_INTAKE/ssi/Project5_TAMPERED_UID_67_Directional_Path_Analysis_2026-7-8-8-19-10.xlsx` | 11,423 | `.xlsx` | `ooxml-excel` | — | `834e68133874ce73d67bf7d4edf58af5d54a03bf5136b8ed577981b9415210c3` |
| `00_REFERENCE_INTAKE/ssi/SRA Large Test File2 POLARIS Output 2.jpg` | 267,217 | `.jpg` | `jpeg` | — | `c7b4636dbd4aa8430fe131ec1b756b58f05127c7f6577429bf90591b886c83bd` |
| `00_REFERENCE_INTAKE/ssi/SRA Large Test File2.mpp` | 9,443,328 | `.mpp` | `ole2-project` | — | `772ca901c5efccdb141b9c07c8bfd54ab8a33026a2b5a9858980fef75f46d8dd` |
| `00_REFERENCE_INTAKE/ssi/SRA Large Test File2_SRA_Results_2026-7-29_11-57-1.xlsx` | 30,363 | `.xlsx` | `ooxml-excel` | — | `43953707629680dd1fdbb12a3efcf0f9f6f9506c1dc025c7b1c9d83cf0f5142d` |
| `00_REFERENCE_INTAKE/ssi/SRA Large Test File2_SRA_Results_2026-8-12_11-59-20.xlsx` | 31,033 | `.xlsx` | `ooxml-excel` | — | `8dd341f28a196a2e645b87b75bdb83dc5caae76a9da228182420d0e51d88d920` |
| `00_REFERENCE_INTAKE/ssi/Sensitivity - Large Test File2_SRA_Results_2026-8-12_11-59-20.xlsx` | 25,990 | `.xlsx` | `ooxml-excel` | — | `d2db89d97d19d975f56a2572c46e4b004cd7c8826fc1949ce7451b576faeae37` |
| `00_REFERENCE_INTAKE/ssi/sra-Polaris Finish Date Confidence S-Curve Results Large Test File2.xlsx` | 65,864 | `.xlsx` | `ooxml-excel` | — | `b2f9db8d81491760d8dd0dc0b63f393c676dd38b9d9a52ae367724ba6cd3a956` |
| `00_REFERENCE_INTAKE/ssi/sra-Polaris Risk Drivers Tornado Results Large Test File2.xlsx` | 65,864 | `.xlsx` | `ooxml-excel` | — | `b2f9db8d81491760d8dd0dc0b63f393c676dd38b9d9a52ae367724ba6cd3a956` |
| `00_REFERENCE_INTAKE/ssi/sra-Polaris SRA  Results Large Test File2.xlsx` | 78,164 | `.xlsx` | `ooxml-excel` | — | `9bf0abb0b544cda6bd891c08e79080c34f2cb37914e08eedc6e35d7fe5540bae` |
| `00_REFERENCE_INTAKE/ssi/sra-Polaris Sensitivity Results Large Test File2.xlsx` | 65,864 | `.xlsx` | `ooxml-excel` | — | `b2f9db8d81491760d8dd0dc0b63f393c676dd38b9d9a52ae367724ba6cd3a956` |
| `00_REFERENCE_INTAKE/styles.css` | 5,760 | `.css` | `text` | — | `3bc3758cdfc2963cd53844cf55b2555b3bc6b72019dbeeb292dbce25dfaeadb4` |
| `00_REFERENCE_INTAKE/support.js` | 63,119 | `.js` | `text` | — | `763cbdcaa2defbe9e91d992ce4918a46e9577cef70930b7410d20b1ab8fb536e` |
| `00_REFERENCE_INTAKE/test_dashboard_perf_contract.py` | 3,013 | `.py` | `text` | — | `74e03580cc81c5719bd45a57c538df89a79c6707168c9066dfcdbe9d05611f70` |
| `00_REFERENCE_INTAKE/themes.css` | 7,659 | `.css` | `text` | — | `e36899b95a17f37e8af010c4e8b1f4225a412727bcbf2f7ebf2e250197161d6e` |
