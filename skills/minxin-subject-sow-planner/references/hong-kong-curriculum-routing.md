# Hong Kong curriculum routing

Record jurisdiction, KLA, Key Stage, subject/programme, exact authority title, edition/version, section/descriptor, source URL or PDF hash, access date, applicability, and alignment status.

The eight Hong Kong KLAs are Chinese Language Education, English Language Education, Mathematics Education, Personal, Social and Humanities Education, Science Education, Technology Education, Arts Education, and Physical Education. Do not infer that an international Grade maps automatically to a Hong Kong Key Stage.

## Source hierarchy

1. Current official subject Curriculum and Assessment Guide or qualification syllabus.
2. Current EDB KLA Curriculum Guide and applicable Key Stage guidance.
3. EDB cross-curricular guidance, including values education, information literacy, generic skills, national/global perspectives, and assessment.
4. School aims, Major Concerns, learner evidence, resources, and calendar.
5. Research-informed pedagogy used transparently as design rationale.

If a syllabus is unverified, state `informed by` and create a QA owner/stop condition. Do not attach EDB or qualification labels to unchanged generic content.

Use the official EDB Curriculum Development portal (`https://www.edb.gov.hk/en/curriculum-development/`) and KLA pages (`https://www.edb.gov.hk/en/curriculum-development/kla/`) to locate the current document. These are routing entry points, not proof of a descriptor. Verify the exact guide and section, store its version/access date, and use `alignment_status=VERIFIED` only after that check.

## International programme boundaries

Verified 2026-08-28 routing sources:

- IB offers four programmes for ages 3–19. MYP is a five-year framework for ages 11–16 with eight subject groups; DP is for ages 16–19 with six subject groups plus TOK, CAS and the Extended Essay. IB programme pages: `https://www.ibo.org/programmes/`, MYP curriculum: `https://www.ibo.org/programmes/middle-years-programme/curriculum/`, DP curriculum: `https://www.ibo.org/programmes/diploma-programme/curriculum/`.
- Cambridge IGCSE is an international qualification generally for ages 14–16 with subject-specific syllabuses and end-of-course assessment that may include written, oral, coursework or practical components. Source: `https://www.cambridgeinternational.org/programmes-and-qualifications/cambridge-upper-secondary/cambridge-igcse/`.
- “GCE” is insufficiently specific. Require the awarding organisation, jurisdiction/regulator, subject specification and assessment objectives. Cambridge International AS & A Level is a separately named route: `https://www.cambridgeinternational.org/programmes-and-qualifications/cambridge-advanced/cambridge-international-as-and-a-levels/`. Ofqual GCE conditions apply only within their stated regulatory scope: `https://www.gov.uk/government/publications/gce-qualification-level-conditions-and-requirements/gce-qualification-level-conditions-and-requirements--2`.

Do not equate IB's eight MYP subject groups with EDB's eight KLAs. If the brief says only `IB`, `IGCSE`, or `GCE`, keep `PLANNING_REQUIRED` until the exact programme, subject syllabus/code, version, grading/assessment regime, and authority are confirmed.
