# The Unofficial Guide

<!-- Replace this line with your name and which corpus you picked. -->

Arianna Mekovich - campus_life Corpus

> **This file is your submission.** Fill it in as you go — most sections get
> written during the milestone that produces them, not at the end.
>
> How the starter works, and every command you'll need, is in `RUNNING.md`.
> Leave that file alone.
>
> **Paste everything as text.** No screenshots, no video. A typed table gets
> full credit; a picture of the same table gets none.
>
> Delete these instruction blocks as you replace them. The `<!-- -->` comments
> are notes to you and don't show up when the page renders — you can leave them
> or remove them.

---

# Unit 1

## What This Does

<!-- Three or four sentences. Which corpus you picked, and the kinds of
     questions your system answers. Write it for someone who has never seen
     this repo.

     Milestone 5. -->

The Unofficial Guide is a document-based question-answering system built for CodePath AI 201. It uses the `campus_life` corpus, which contains 88 short student-life documents covering topics such as housing, dining, academics, and financial aid. The application processes these documents, generates text embeddings, and stores them in a vector database to retrieve information relevant to a user's question. It uses the retrieved documents to generate answers with source citations and a relevance gate to prevent unsupported responses.

## Chunking Strategy

**Chunk size:** 400 characters (target)
**Overlap:** 0 characters

<!-- What about YOUR documents made you pick these numbers? Short posts and
     long sectioned guides don't want the same chunking, and "800 seemed
     reasonable" earns nothing. Point at something you noticed when you read
     the documents in Milestone 1.

     If you changed your mind partway through, say so and say why. That's worth
     more than pretending you got it right first time.

     Milestone 3. -->

I chose a paragraph-aware chunking strategy because my `campus_life` corpus contains 88 short student-life posts, averaging 317 characters per document.

The original chunker used fixed 800-character windows with a 120-character overlap. It produced 88 chunks, which meant that each document remained a single chunk.

My custom `split_documents()` function divides documents at paragraph and sentence boundaries rather than cutting them at fixed character positions. Short paragraphs are combined when they fit within the target chunk size, while longer paragraphs are split between sentences.

I chose a target of 400 characters because most of the documents are already relatively short. This allows shorter posts to remain together while separating longer posts into smaller chunks.

I chose zero overlap because the documents contain short, mostly self-contained passages. The goal is to preserve complete sentences without unnecessarily duplicating information between chunks.

The chunk size is a target rather than a strict maximum because a sentence longer than 400 characters is preserved instead of being split in the middle.

### Initial Results

| Measurement | Original Chunker | Custom Chunker |
|---|---:|---:|
| Documents | 88 | 88 |
| Total chunks | 88 | 100 |
| Average chunk length | 317 | 278 |
| Shortest chunk | 178 | 94 |
| Longest chunk | 549 | 400 |

The custom chunker produced 12 additional chunks and reduced the average chunk length while preserving sentence boundaries in the five sampled chunks.

## Sample Chunks

<!-- Five chunks, pasted as text. Label each one and name the file it came from
     AND the function that produced it — the grader checks your code against
     what you claim here.

     `python app.py chunks -n 5` prints all three for you. Copy them straight
     across.

     Milestone 3. -->

**Chunk 1** — source: `admin_add_drop_deadline.txt#0` — produced by: `chunker.py::split_documents`

```text
On the add/drop deadline

You can add a course through the end of the second week. Dropping is a longer window — through the end of week six — but a drop after week two shows as a W on your transcript. Nothing anywhere on the registrar's site says this plainly, and students find out from each other.
```

**Chunk 2** — source: `course_cs_210.txt#0` — produced by: `chunker.py::split_documents`

```text
CS 210 Data Structures

I'm a junior and I've done this twice now. Format is lecture with weekly labs; slides go up after class, not before. Assessment: two midterms and a final, all drawn from lecture material rather than the textbook. Midterms are curved, the final is not.

Expect 8 to 10 hours a week outside class.
```

**Chunk 3** — source: `course_math_220_workload.txt#0` — produced by: `chunker.py::split_documents`

```text
Workload for MATH 220 Linear Algebra

People keep asking so: 6 to 8 hours a week, almost all of it on problem sets. That's real time, not optimistic time.

It's front-loaded — the first month is heavier than the rest, partly because you're learning the format.
```

**Chunk 4** — source: `dining_the_ridgeway_cafe_followup.txt#0` — produced by: `chunker.py::split_documents`

```text
Re: The Ridgeway Café

Adding to what people have said about The Ridgeway Café. The wait figure of 10 to 15 minutes at 12:30 matches what I've seen. If you're trying to eat between classes, go before 11:45 and it's a different building entirely.

Also worth saying: seating is tight; about 40 seats for a building of 900. Nobody tells you this at orientation.
```

**Chunk 5** — source: `housing_morrow_house.txt#0` — produced by: `chunker.py::split_documents`

```text
Morrow House — what it's actually like

Just finished a year in this building. Built 1954, partially renovated 2008. Rooms are singles and doubles, hall bathrooms.

The good: cheapest housing tier by about $900 a year, and the singles are real singles.

The bad: known damp problem on the ground floor; two rooms were taken offline in 2024.
```

## Sample Answer

<!-- One complete question and answer, pasted as text, with the source line
     visible. Milestone 4. -->

**Question:** How are juniors and seniors prioritized in the housing lottery?

**Answer:**

Juniors and seniors are ordered by accumulated credit hours first, with ties broken randomly in the housing lottery.

Source: admin_housing_lottery.txt

**My relevance cutoff: 0.6**

<!-- The number you set in config.py, and how you got there.

     You ran five questions your corpus covers and the five in OUT_OF_SCOPE
     that it clearly doesn't, and wrote down the best distance for each. What
     did those two groups look like? Where was the gap? Put the actual numbers
     here — the table below wants all ten rows.

     Milestone 4. -->

I selected a relevance cutoff of 0.6 after comparing the best retrieval distances for five questions covered by my corpus and five out-of-scope questions.

The in-corpus questions had best distances ranging from 0.1379 to 0.3962, while the out-of-scope questions had best distances ranging from 0.8246 to 0.9340.

There was a clear gap between the highest in-corpus distance (0.3962) and the lowest out-of-scope distance (0.8246).

Since 0.6 falls within this gap, I kept the original cutoff. It accepted all five in-corpus questions and rejected all five out-of-scope questions during retrieval testing.

### Retrieval Distance Results

| Question | In corpus? | Best distance |
|---|---|---:|
| When can students declare their major? | Yes | 0.3560 |
| How do work-study earnings affect financial aid compared to non-work-study campus jobs? | Yes | 0.1379 |
| How are juniors and seniors prioritized in the housing lottery? | Yes | 0.2050 |
| When do unused dining dollars expire? | Yes | 0.3675 |
| Which campus housing building is closest to the science quad? | Yes | 0.3962 |
| What is the capital of Mongolia? | No | 0.8246 |
| How do I change the oil in a diesel engine? | No | 0.9340 |
| Who won the 1994 World Cup? | No | 0.8859 |
| What is the recommended dosage of ibuprofen for a headache? | No | 0.8442 |
| How do I write a for loop in Rust? | No | 0.8907 |

### Grounding and Relevance Gate Verification

I tested the grounding instructions using the housing lottery question. The model generated an answer using the retrieved documents and identified `admin_housing_lottery.txt` as its source.

I also tested an out-of-scope question:

**Question:** What is the capital of Mongolia?

**Response:**

I don't have enough information about that.

The relevance gate rejected this question because its best retrieval distance was 0.8246, which exceeded the cutoff of 0.6. The application returned the refusal without making a model call.

## How I Used AI

<!-- Two specific moments. For each: what you asked for, what came back, and
     what you changed about it.

     "I asked Claude to write the chunking function from my notes. It ignored
     the overlap, so I added that myself" is the level of detail we're after.
     "I used AI to help me code" is not.

     Milestone 5. -->

**1. Developing my custom chunking strategy**

I used ChatGPT to help develop a custom chunking function for my `campus_life` corpus. I provided the original `chunker.py`, `config.py`, and the results from my initial document indexing. ChatGPT suggested a paragraph-aware chunking strategy using a target size of 400 characters and zero overlap.

I implemented the suggested function and tested it against my documents. The custom chunker generated 100 chunks compared to the original 88, with an average chunk length of 278 characters. I reviewed five generated chunks to verify that they preserved complete sentences and retained their source information. I also chose to keep my original `save_chunk()` implementation rather than apply an optional indexing optimization suggested by ChatGPT.

**2. Selecting and verifying my relevance cutoff**

I used ChatGPT to help interpret the retrieval distances from my five in-corpus questions and five out-of-scope questions. I provided the actual retrieval results and asked for help selecting an appropriate relevance cutoff.

ChatGPT identified a gap between the highest in-corpus distance (0.3962) and the lowest out-of-scope distance (0.8246). Based on these measurements, I decided to keep the original cutoff of 0.6 rather than change it without evidence.

I then tested a housing lottery question to verify that the model generated a grounded answer with a source citation. I also tested an unrelated question about Mongolia and confirmed that the relevance gate rejected it without making a model call. 


<!-- ── Stretch features ─────────────────────────────────────────────────────
     Doing one? Say so here BEFORE you start. A feature this README never
     claims earns nothing.
     ───────────────────────────────────────────────────────────────────────── -->

## Stretch Features:

I plan to implement the following extra-credit features in my project:
     
     **Metadata Filtering:** Allow users to narrow search results by document source or date.
     **Conversational Memory:** Allow users to ask follow-up questions that build on previous questions and answers.
     **Second Embedding Model:** Implement an alternative embedding model and compare its retrieval results with the original model to identify differences in performance.

### Metadata Filtering — Implemented

I implemented metadata filtering to allow users to narrow retrieval results to a specific source document.

My application stores source filenames as metadata in ChromaDB. I added an optional `--source` argument to the `retrieve` and `ask` commands, which filters the vector search before the results are passed to the model.

**Example:**

```bash
python app.py ask "How are juniors and seniors prioritized in the housing lottery?" --source admin_housing_lottery.txt
```

**Testing Results:**

- Filtering to `admin_housing_lottery.txt` returned only the requested document and generated a correct answer with a source citation.
- Filtering a housing lottery question to `admin_dining_dollars.txt` produced a best distance of 0.8041, exceeding the relevance cutoff of 0.6. The system rejected the question.
- Filtering to a nonexistent filename returned an empty-results message without crashing.

The relevance gate and grounding instructions remain active when metadata filtering is enabled.


---

# Unit 2

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     unit 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

<!-- Your five criteria, three runs each. `python run_eval.py --label before`
     runs the questions, puts the OUT_OF_SCOPE ones through the gate, and
     writes it all into results/ for you. Targets come from criteria.md; the
     verdict column is your call.

     Criterion 3 is measured in one deterministic pass rather than three, so
     the same number goes in all three run columns. That's correct, not lazy.

     Milestone 1. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

<!-- Underneath, paste the REAL output for each criterion from one of your
     runs — the actual text your system produced, not a description of it.
     Name the file and function that produced it. -->

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |

## Diagnoses

<!-- For each miss: which stage caused it, and how. The stage alone isn't
     enough — you need the mechanism.

     Not a diagnosis: "Question 3 didn't work."
     A diagnosis:     "Question 3 asks about laundry costs. The answer is in
                       one sentence that got split across two chunks, so
                       neither chunk on its own contains it."

     The five stages: loading → chunking → embedding → retrieval → generation.

     Look for a pattern. If three misses all ask about numbers, that's one
     problem, not three.

     Missed nothing? Say so, then say honestly whether your targets were set
     low, and which one you'd tighten and to what.

     Milestone 3. -->

## The Improvement

**What I changed:**

**Why I picked it:**

<!-- Connect it to a specific diagnosis above in one sentence. If you can't,
     you picked a fix because it sounded impressive. -->

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

**Did it help?**

<!-- Say plainly whether it did, and how you know. If it made things worse,
     say that — a change that backfired, honestly reported, earns full credit
     and is more interesting than one that worked. What matters is that you can
     tell.

     Milestone 4. -->

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->
