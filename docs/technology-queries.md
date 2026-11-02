# The technology queries

This document is written by `scripts/write_technology_queries.py` from the
files the package ships. Do not edit it by hand.

The technology queries tag a text with advanced digital technologies. A
query is a list of terms per group; a text is tagged with a group when one of
the group's terms occurs in it. They are keyword queries, not a trained
model. Two versions ship:

- **Simplified** (`src/sdg_tech_tagger/adt/simplified/`): 285 terms in
  six groups. Terms are matched as they are written.
- **Extended** (`src/sdg_tech_tagger/adt/extended/`): 868 terms in seven
  groups, the six of the simplified query and a group of umbrella terms. It
  has more terms per group, for a higher recall at some cost of precision.
  It also accepts the regular plural of a term, the closed spelling of a
  term written with a hyphen, and reads a decimal number as one word. The
  source of each of its terms is given below; the keys resolve in
  [`CREDITS.md`](../CREDITS.md).

275 terms are in both versions, written the same way.

## How a term is matched

The text and the terms are put in the same form: lower case, and every run
of characters that are not letters or digits becomes one space. A term then
matches a run of whole words of the text.

- A term of several words matches those words in that order, side by side:
  `computer vision` matches "Computer-Vision" and "computer vision", not
  "vision of the computer".
- `*` at the end of a word stands for any ending of that word, the empty
  one included: `robot*` matches "robot", "robots" and "robotics". It never
  reaches into the next word.
- In the extended query only:
  - a term also matches its regular plural (`s`, `es`, or `ies` for a `y`
    after a consonant), except `ai`; a term ending in `*` or in a digit
    takes no plural;
  - a term written with a hyphen also matches its closed spelling:
    `back-propagation` matches "backpropagation";
  - a dot or comma between two digits keeps the number whole: `5g` does not
    match "0.5g", and `industry 4.0` does not match "industry 4 0".

In Python, `sdg_tech_tagger.adt.translate.flag` applies a version to a table
of texts; see `README.md`.

## The Web of Science files

- `adt/simplified/*.txt`: the simplified query in Web of Science syntax, one
  file per group. These are the queries as run on the Web of Science.
- `adt/extended/*.txt`: the terms of the extended query in Web of Science
  syntax, without the plural, hyphen and decimal rules, so they do not give
  the extended query when run as they are.
- `adt/extended_wos/`: the extended query with every plural and closed
  spelling written out as a term of its own, one file per group and
  `ALL.txt` for all groups. The decimal rule cannot be written in Web of
  Science syntax, and the `TS` field also reads keywords; its `README.md`
  says where the files and the package differ.

## Terms per group

| group | simplified | extended | in both |
|---|---:|---:|---:|
| AI, Artificial intelligence and big data analytics | 150 | 378 | 133 |
| IOT, Internet of Things | 22 | 92 | 22 |
| CI, Computing infrastructure | 53 | 161 | 50 |
| BL, Blockchain | 6 | 47 | 6 |
| ROB, Robotics | 25 | 79 | 24 |
| AM, Additive manufacturing | 29 | 85 | 28 |
| UMBRELLA, Umbrella terms | 0 | 26 | 0 |
| all groups | 285 | 868 | 263 |

"In both" counts the terms a group has in both versions. A term can sit in two groups: in the simplified query `data center*` and `data centre*` are in AI and CI, and in the extended query `tinyml` is in two groups. The last row counts terms per group, so a term in two groups counts twice there; the count of distinct terms is 283 simplified and 867 extended, 275 of them in both, whatever their group.

## AI: Artificial intelligence and big data analytics

Systems that infer from their input how to produce outputs such as predictions, content, recommendations or decisions: machine learning and deep learning of every kind, and logic- and knowledge-based approaches such as expert systems. Big data analytics and data mining are counted here when they are the method of analysis.

### Simplified, 150 terms

Terms not in the extended query are marked with a dagger (†).

`adaptive boosting`, `adversarial network`, `albert`, `apache cassandra`, `apache hive`, `apache kafka`, `apache spark`, `artificial intellig*`, `artificial neural network`, `artificial realit*` †, `augmented realit*` †, `autoencoder`, `automated reasoning`, `backpropagation`, `bayesian learning`, `bayesian network`, `bidirectional encoder representations from transformer`, `big data`, `bigtable`, `brownboost`, `computer vision`, `computer-mediated realit*` †, `convolutional neural network`, `data center*` †, `data centre*` †, `data mining`, `data science`, `deep belief network`, `deep convolutional neural network`, `deep generative model`, `deep learning`, `deep neural network`, `differential evolution algorithm`, `diffusion model`, `distributed file system*`, `docker`, `ensemble learning`, `evolutionary algorithm`, `expert system*`, `extreme machine learning`, `face detection`, `feature extraction`, `generative adversarial network`, `generative adversarial network*`, `generative artificial intelligence`, `generative model`, `generative pre-trained transformer`, `genetic algorithm`, `genetic programming`, `gesture recognition`, `gradient boosting`, `gradient tree boosting`, `gravitational search algorithm`, `hadoop`, `hbase`, `hebbian learning`, `image classification`, `image model`, `image recognition`, `image segmentation`, `information retrieval`, `instance-based learning`, `instruction model`, `intelligent machine*`, `k-means`, `keras`, `kernel learning`, `kernel machine`, `knowledge representation`, `language model`, `large action model`, `large language model`, `large-scale data*`, `latent dirichlet allocation`, `latent semantic analysis`, `logitboost`, `long short term memory`, `lpboost`, `machine intelligence`, `machine learning`, `machine translation`, `madboost`, `mapreduce`, `markovian`, `masked language model`, `massive data*`, `memetic algorithm`, `meta-learning`, `mixed realit*` †, `multi-layer perceptron`, `multilayer perceptron*`, `multilingual language model`, `multimodal large language model`, `natural language generation`, `natural language processing`, `natural language understanding`, `nearest neighbour algorithm`, `neural net*`, `neural network`, `neural turing machine`, `object detection`, `object identification`, `object recognition`, `particle swarm optimisation`, `pattern recognition`, `policy gradient methods`, `pose estimation`, `pytorch`, `q-learning`, `random forest`, `rankboost`, `recurrent neural network`, `regression tree`, `reinforcement learning`, `relational learning`, `retrieval augmented generation`, `roberta`, `semantic search`, `semi-supervised learning`, `sentiment analysis`, `small language model`, `speech recognition`, `statistical language model`, `statistical learning`, `statistical relational learning`, `stochastic block model`, `stochastic gradient`, `supervised learning`, `support vector machine`, `support vector regression`, `swarm optimisation`, `task-based generative model`, `temporal difference learning`, `tensorflow`, `text classification`, `text-to-image model`, `text-to-video model`, `totalboost`, `transfer learning`, `transformer`, `transformer network*`, `unsupervised learning`, `variational inference`, `vector machine`, `virtual realit*` †, `vision transformer`, `voice recognition`, `wasserstein gan`, `word2vec`, `xgboost`

### Extended, 378 terms

| term | source | also in simplified |
|---|---|---|
| `action recognition` | OECD20; AIW21 |  |
| `activation function*` | LIU21 |  |
| `active learning` | CSET20; AIW21; WIPO19 |  |
| `activity recognition` | OECD20; TANG23 |  |
| `actor-critic algorithm*` | LIU21 |  |
| `adaboost*` | LIU21 |  |
| `adaptive boosting` | LIU21 | yes |
| `adversarial learning` | LIU21 |  |
| `adversarial network` | evidence B: OECD20, AIW | yes |
| `ai` | UNCTAD21; ATI21; TANG23 (recall stage before a classifier) |  |
| `albert` | own, from the simplified query | yes |
| `alphafold` | WIPO24 |  |
| `anfis` | TANG23; LIU21 (neuro-fuzzy) |  |
| `ann` | TANG23 |  |
| `anomaly detection` | AIW21; CSET20 |  |
| `ant colony algorithm*` | own, added for recall |  |
| `ant colony optimisation` | OECD20; TANG23 |  |
| `ant colony optimization` | OECD20; TANG23 |  |
| `ant colony system*` | own, added for recall |  |
| `artificial bee colony` | OECD20; TANG23 |  |
| `artificial general intelligence` | AIW21 |  |
| `artificial intellig*` | evidence B: Liu+, WIPO19-K1, OECD20, CSET20, Tang23, Tang23pre | yes |
| `artificial intelligen*` | LIU21 |  |
| `artificial neural network` | evidence B: OECD20, AIW, Tang23, Tang23pre | yes |
| `association rule*` | OECD20 |  |
| `attention mechanism*` | own, added for recall |  |
| `autoencoder` | evidence B: Liu+, OECD20, Tang23pre | yes |
| `autoencoder*` | LIU21 |  |
| `automated reasoning` | own, from the simplified query | yes |
| `autonomous weapon*` | OECD20 |  |
| `back-propagation` | CSET20 |  |
| `back-propagation algorithm*` | LIU21 |  |
| `back-propagation learning` | LIU21 |  |
| `back-propagation net*` | LIU21 |  |
| `backpropagation` | evidence B: WIPO19-K2, OECD20, CSET20, Tang23pre | yes |
| `backpropagation algorithm*` | LIU21 |  |
| `backpropagation learning` | LIU21 |  |
| `backpropagation net*` | LIU21 |  |
| `bayesian learning` | evidence B: OECD20 | yes |
| `bayesian network` | evidence B: WIPO19-K1, OECD20, Tang23pre | yes |
| `bidirectional encoder representations from transformer` | own, from the simplified query | yes |
| `big data` | evidence B: AIW, Tang23pre | yes |
| `boltzmann machine*` | LIU21 |  |
| `boosting algorithm*` | LIU21 |  |
| `bp learning` | LIU21 |  |
| `bp network*` | LIU21 |  |
| `brownboost` | evidence B: OECD20 | yes |
| `business intelligence` | MMM21; AIW21 |  |
| `case-based reasoning` | AIW21 |  |
| `catboost` | own, added for recall |  |
| `character recognition` | WIPO19; CSET20 |  |
| `chat-bot*` | EUROSTAT23; ATI21; OECD20; MMM21; ISO8373 |  |
| `chatgpt` | WIPO24 |  |
| `classification algorithm*` | LIU21 |  |
| `classification tree*` | OECD20 |  |
| `cnn` | TANG23 |  |
| `co-training` | LIU21 |  |
| `cognitive comput*` | OECD17ICT; ATI21; BIANCHINI26 | yes |
| `collaborative filtering` | OECD20; AIW21 |  |
| `committee machine*` | LIU21 |  |
| `community detection` | OECD20 |  |
| `computation* intelligen*` | LIU21 |  |
| `computer vision` | evidence B: OECD20, CSET20, Tang23, Tang23pre | yes |
| `computer-aided diagnosis` | CSET20 |  |
| `concept* drift` | LIU21 |  |
| `conditional random field*` | LIU21 |  |
| `connectionis*` | LIU21 |  |
| `continual learning` | own, added for recall |  |
| `contrastive learning` | own, added for recall |  |
| `conversational agent*` | own, added for recall |  |
| `convolution* net*` | LIU21 |  |
| `convolutional neural network` | evidence B: OECD20, AIW, Tang23, Tang23pre | yes |
| `dall-e` | WIPO24 |  |
| `data analytics` | ATI21; AIW21 |  |
| `data mining` | evidence B: WIPO19-K1, OECD20(italic), AIW, Tang23pre | yes |
| `data science` | own, from the simplified query | yes |
| `decision forest*` | LIU21 |  |
| `decision tree*` | WIPO19; OECD20; TANG23 |  |
| `deep belief net*` | LIU21 |  |
| `deep belief network` | evidence B: Liu+, OECD20 | yes |
| `deep convolutional neural network` | evidence B: OECD20 | yes |
| `deep generative model` | evidence B: WIPO24 | yes |
| `deep learning` | LIU21 | yes |
| `deep net*` | LIU21 |  |
| `deep neural network` | evidence B: OECD20, AIW, Tang23, Tang23pre | yes |
| `denoising diffusion probabilistic model*` | WIPO24 |  |
| `dictionary learning` | OECD20 |  |
| `differential evolution` | OECD20; TANG23 |  |
| `differential evolution algorithm` | evidence B: OECD20 | yes |
| `diffusion model` | own, from the simplified query | yes |
| `dnn` | TANG23 |  |
| `echo state* net*` | LIU21 |  |
| `emotion recognition` | OECD20; TANG23 |  |
| `ensemble learning` | LIU21 | yes |
| `evolutionary algorithm` | evidence B: OECD20, AIW, CSET20, Tang23 | yes |
| `evolutionary computation` | OECD20; ANZSRC20 |  |
| `expert system*` | LIU21 | yes |
| `extreme learning machine*` | LIU21 |  |
| `extreme machine learning` | evidence B: OECD20 | yes |
| `face detection` | own, from the simplified query | yes |
| `face recognition` | OECD20; WIPO19; AIW21; CSET20 |  |
| `facial expression recognition` | OECD20; TANG23; CSET20 |  |
| `facial recognition` | CSET20; WIPO19 |  |
| `feature engineering` | OECD20 |  |
| `feature extraction` | evidence B: OECD20, AIW, CSET20, Tang23pre | yes |
| `feature learning` | LIU21 |  |
| `feature selection` | OECD20; CSET20; WIPO19 |  |
| `federated learning` | own, added for recall |  |
| `feed-forward net*` | LIU21 |  |
| `feedforward net*` | LIU21 |  |
| `few-shot` | own, added for recall |  |
| `foundation model*` | own, added for recall |  |
| `fuzzy inference` | OECD20 (fuzzy system); TANG23 |  |
| `fuzzy logic` | WIPO19; OECD20; AIW21; ANZSRC20 |  |
| `genai` | own, added for recall |  |
| `generalisation error*` | LIU21 |  |
| `generalization error*` | LIU21 |  |
| `generative adversarial net*` | LIU21 |  |
| `generative adversarial network` | evidence B: Liu+, OECD20, AIW, CSET20, Tang23, Tang23pre, WIPO24 | yes |
| `generative adversarial network*` | evidence B: Liu+, OECD20, AIW, CSET20, Tang23, Tang23pre, WIPO24 | yes |
| `generative ai` | WIPO24 |  |
| `generative artificial intelligence` | evidence B: WIPO24 | yes |
| `generative model` | evidence B: AIW, WIPO24 | yes |
| `generative modeling` | WIPO24 |  |
| `generative modelling` | own, added for recall |  |
| `generative pre-trained transformer` | evidence B: WIPO24 | yes |
| `genetic algorithm` | evidence B: WIPO19-K1, OECD20, AIW, Tang23 | yes |
| `genetic programming` | LIU21 | yes |
| `gesture recognition` | evidence B: OECD20, AIW, Tang23pre | yes |
| `github copilot` | WIPO24 |  |
| `gnn` | TANG23 |  |
| `gpt-2` | own, added for recall |  |
| `gpt-3` | WIPO24 |  |
| `gpt-3.5` | own, added for recall |  |
| `gpt-4` | WIPO24 |  |
| `gpt-4.0` | own, added for recall |  |
| `gpt-4o` | own, added for recall |  |
| `gpt4` | WIPO24 |  |
| `gradient boost*` | LIU21; OECD20 |  |
| `gradient boosting` | LIU21 | yes |
| `gradient tree boosting` | evidence B: WIPO19-K1, OECD20 | yes |
| `grammatical inference` | LIU21 |  |
| `graph convolutional` | own, added for recall |  |
| `graph learning` | LIU21 |  |
| `graph* kernel*` | LIU21 |  |
| `graphical model*` | OECD20; AIW21; CSET20 |  |
| `gravitational search algorithm` | evidence B: OECD20(italic) | yes |
| `handwriting recognition` | WIPO19; CSET20 |  |
| `hebbian learning` | evidence B: OECD20 | yes |
| `hidden markov model*` | OECD20; WIPO19; TANG23 |  |
| `hierarchical clustering` | OECD20; CSET20 |  |
| `hopfield net*` | LIU21 |  |
| `hypergraph* learning` | LIU21 |  |
| `image classification` | evidence B: OECD20, CSET20, Tang23pre | yes |
| `image model` | own, from the simplified query | yes |
| `image recognition` | evidence B: OECD20 | yes |
| `image retrieval` | OECD20; AIW21; CSET20; TANG23 |  |
| `image segmentation` | evidence B: OECD20(italic), Tang23, Tang23pre | yes |
| `incremental learning` | LIU21 |  |
| `inductive logic programming` | LIU21 |  |
| `information extraction` | AIW21; CSET20 |  |
| `information retrieval` | evidence B: AIW, CSET20 | yes |
| `instance-based learning` | evidence B: OECD20 | yes |
| `instruction model` | own, from the simplified query | yes |
| `intelligent agent*` | LIU21 |  |
| `intelligent algorithm*` | LIU21 |  |
| `intelligent machine*` | own, from the simplified query | yes |
| `k-means` | evidence B: OECD20 | yes |
| `k-nearest neighbo*` | CSET20 |  |
| `keras` | own, from the simplified query | yes |
| `kernel learning` | evidence B: OECD20 | yes |
| `kernel machine` | own, from the simplified query | yes |
| `knn` | own, added for recall |  |
| `knowledge representation` | evidence B: CSET20 | yes |
| `knowledge-based system*` | CSET20; AIW21 |  |
| `label propagation` | LIU21 |  |
| `language model` | own, from the simplified query | yes |
| `language model*` | WIPO24 |  |
| `large action model` | own, from the simplified query | yes |
| `large language model` | evidence B: WIPO24 | yes |
| `large-scale data*` | own, from the simplified query | yes |
| `latent dirichlet allocation` | evidence B: WIPO19-K1, OECD20 | yes |
| `latent semantic analysis` | evidence B: WIPO19-K1, OECD20 | yes |
| `lazy learning` | LIU21 |  |
| `learning algorithm*` | LIU21 |  |
| `learning automata` | OECD20 |  |
| `learning automaton` | own, added for recall |  |
| `learning model*` | LIU21 |  |
| `learning to rank*` | LIU21 |  |
| `learning-based` | own, added for recall |  |
| `lightgbm` | own, added for recall |  |
| `link prediction` | OECD20 |  |
| `liquid state machine*` | LIU21 |  |
| `llm` | own, added for recall |  |
| `logitboost` | evidence B: OECD20 | yes |
| `long short term memory` | evidence B: Liu+, Tang23 | yes |
| `long short-term memory` | LIU21 |  |
| `lpboost` | evidence B: OECD20 | yes |
| `lstm` | TANG23 |  |
| `machine intelligence` | evidence B: Liu+, OECD20 | yes |
| `machine learning` | evidence B: Liu+, WIPO19-K1, OECD20, CSET20, Tang23 | yes |
| `machine translation` | evidence B: OECD20, AIW, CSET20 | yes |
| `machine vision` | OECD20; TANG23 |  |
| `machine* intelligen*` | LIU21 |  |
| `machine* learning` | LIU21 |  |
| `machine-learned ranking` | LIU21 |  |
| `madaboost` | OECD20 |  |
| `madboost` | own, from the simplified query | yes |
| `manifold learning` | LIU21 |  |
| `manifold regularisation` | LIU21 |  |
| `manifold regularization` | LIU21 |  |
| `markovian` | evidence B: OECD20(italic) | yes |
| `masked language model` | own, from the simplified query | yes |
| `massive data*` | own, from the simplified query | yes |
| `memetic algorithm` | evidence B: OECD20 | yes |
| `meta-learning` | evidence B: OECD20 | yes |
| `metric learning` | LIU21 |  |
| `mixture of expert*` | LIU21 |  |
| `multi* class classification` | LIU21 |  |
| `multi* instance learning` | LIU21 |  |
| `multi* kernel* learning` | LIU21 |  |
| `multi* label classification` | LIU21 |  |
| `multi* label learning` | LIU21 |  |
| `multi* task learning` | LIU21 |  |
| `multi-agent learning` | LIU21 |  |
| `multi-agent system*` | WIPO19; OECD20; TANG23 |  |
| `multi-layer perceptron` | evidence B: OECD20 | yes |
| `multiagent learning` | LIU21 |  |
| `multiclass classification` | LIU21 |  |
| `multiinstance learning` | LIU21 |  |
| `multikernel* learning` | LIU21 |  |
| `multilabel classification` | LIU21 |  |
| `multilabel learning` | LIU21 |  |
| `multilayer perceptron*` | evidence B: WIPO19-K1, Tang23pre | yes |
| `multilingual language model` | own, from the simplified query | yes |
| `multimodal large language model` | own, from the simplified query | yes |
| `multitask learning` | LIU21 |  |
| `naive bayes` | TANG23 |  |
| `naive bayes* classifi*` | LIU21 |  |
| `named entity recognition` | own, added for recall |  |
| `natural language generation` | evidence B: WIPO19-K1, OECD20, AIW, CSET20 | yes |
| `natural language processing` | LIU21 | yes |
| `natural language understanding` | LIU21 | yes |
| `nearest neighbo* algorithm*` | OECD20 |  |
| `nearest neighbo* classif*` | own, added for recall |  |
| `nearest neighbor algorithm` | OECD20 (British form in the WoS file); CSET20 |  |
| `nearest neighbour algorithm` | evidence B: OECD20 | yes |
| `neocognitron*` | LIU21 |  |
| `neural gas` | LIU21 |  |
| `neural model*` | LIU21 |  |
| `neural net*` | LIU21 | yes |
| `neural network` | evidence B: Liu+, WIPO19-K1, OECD20, AIW, CSET20, Tang23pre | yes |
| `neural radiance field*` | WIPO24 |  |
| `neural turing machine` | evidence B: OECD20 | yes |
| `neuro dynamic programming` | LIU21 |  |
| `neuro fuzzy` | LIU21 |  |
| `neuro-computing` | LIU21 |  |
| `neuro-evolution` | LIU21 |  |
| `neuro-robotic*` | LIU21 |  |
| `neurocomputing` | LIU21 |  |
| `neurodynamic programming` | LIU21 |  |
| `neuroevolution` | LIU21 |  |
| `neurofuzzy` | LIU21 |  |
| `neurorobotic*` | LIU21 |  |
| `nlp` | TANG23 |  |
| `object detection` | evidence B: OECD20, Tang23pre | yes |
| `object identification` | own, from the simplified query | yes |
| `object recognition` | evidence B: OECD20, AIW, CSET20, Tang23pre | yes |
| `one class classifi*` | LIU21 |  |
| `one-shot learning` | CSET20 |  |
| `pac learning` | LIU21 |  |
| `particle swarm` | TANG23 |  |
| `particle swarm optimisation` | evidence B: OECD20 | yes |
| `particle swarm optimization` | OECD20 (British form in the WoS file); LIU21 |  |
| `pattern recognition` | evidence B: OECD20, AIW, CSET20, Tang23pre | yes |
| `pcnn` | LIU21 |  |
| `pedestrian detection` | OECD20 |  |
| `perceptron*` | LIU21 |  |
| `policy gradient methods` | evidence B: OECD20 | yes |
| `pose estimation` | evidence B: Tang23pre | yes |
| `predictive analytics` | WIPO19; ATI21 |  |
| `probabl* approximate* correct learning` | LIU21 |  |
| `prompt engineering` | WIPO24 |  |
| `pulse coupled neural net*` | LIU21 |  |
| `pytorch` | own, from the simplified query | yes |
| `q learning` | LIU21 |  |
| `q-learning` | evidence B: Liu+, OECD20, AIW | yes |
| `question answering` | AIW21; WIPO19 |  |
| `radial basis function net*` | LIU21 |  |
| `random forest` | evidence B: Liu+, WIPO19-K1, OECD20, CSET20, Tang23, Tang23pre | yes |
| `random forest*` | LIU21 |  |
| `rankboost` | evidence B: WIPO19-K1, OECD20 | yes |
| `rbf net*` | LIU21 |  |
| `rbfnn*` | LIU21 |  |
| `recommendation system*` | WIPO19; CSET20 |  |
| `recommender system*` | OECD20; AIW21; CSET20; WIPO19; TANG23 |  |
| `recurrent neural network` | evidence B: OECD20, AIW, Tang23, Tang23pre | yes |
| `regression tree` | evidence B: OECD20 | yes |
| `reinforced learning` | own, added for recall |  |
| `reinforcement learning` | LIU21 | yes |
| `relational learning` | evidence B: OECD20 | yes |
| `relevance vector* machine*` | LIU21 |  |
| `representation learning` | LIU21 |  |
| `reservoir computing` | LIU21 |  |
| `resnet*` | own, added for recall |  |
| `retrieval augmented generation` | evidence B: WIPO24 | yes |
| `rnn` | TANG23 |  |
| `roberta` | own, from the simplified query | yes |
| `robot* learning` | LIU21 |  |
| `robotic process automation` | EUROSTAT23 |  |
| `rule learning` | OECD20 |  |
| `rule* induction` | LIU21 |  |
| `rule-based learning` | OECD20 |  |
| `rule-based system*` | LIU21 |  |
| `self-organising map` | OECD20; TANG23 |  |
| `self-organizing map` | OECD20; TANG23 |  |
| `semantic search` | own, from the simplified query | yes |
| `semantic segmentation` | TANG23; ATI21 |  |
| `semantic web` | OECD20; AIW21; TANG23 |  |
| `semi-supervised learning` | evidence B: WIPO19-K1, OECD20, AIW, CSET20 | yes |
| `sentiment analysis` | evidence B: OECD20, AIW, Tang23, Tang23pre | yes |
| `similarity learning` | LIU21 |  |
| `small language model` | own, from the simplified query | yes |
| `sparse representation` | OECD20 |  |
| `spectral clustering` | OECD20 |  |
| `speech processing` | AIW21; CSET20 |  |
| `speech recognition` | evidence B: WIPO19-K2, OECD20, AIW, CSET20 | yes |
| `speech synthesis` | AIW21; CSET20 |  |
| `speech to text` | OECD20 |  |
| `statistical language model` | own, from the simplified query | yes |
| `statistical learning` | evidence B: AIW, CSET20 | yes |
| `statistical relation* learning` | LIU21 |  |
| `statistical relational learning` | evidence B: Liu+, OECD20, AIW | yes |
| `stochastic block model` | own, from the simplified query | yes |
| `stochastic gradient` | evidence B: OECD20 | yes |
| `string kernel*` | LIU21 |  |
| `supervised learning` | LIU21 | yes |
| `support vector machine` | evidence B: Liu+, WIPO19-K1, OECD20, AIW, CSET20, Tang23, Tang23pre | yes |
| `support vector regression` | evidence B: Liu+, OECD20, Tang23pre | yes |
| `support* vector* machine*` | LIU21 |  |
| `support* vector* regression` | LIU21 |  |
| `svm` | TANG23 |  |
| `swarm intelligence` | WIPO19; OECD20; AIW21 |  |
| `swarm optimisation` | evidence B: OECD20 | yes |
| `swarm optimization` | OECD20 (British form in the WoS file) |  |
| `task-based generative model` | own, from the simplified query | yes |
| `temporal difference learning` | LIU21 | yes |
| `tensorflow` | own, from the simplified query | yes |
| `text classification` | evidence B: AIW, Tang23pre | yes |
| `text mining` | AIW21; CSET20; OECD20 |  |
| `text to speech` | OECD20 |  |
| `text-to-image generation` | WIPO24 |  |
| `text-to-image model` | own, from the simplified query | yes |
| `text-to-image prompt` | WIPO24 |  |
| `text-to-video model` | own, from the simplified query | yes |
| `tinyml` | own, added for recall |  |
| `topic model*` | OECD20 |  |
| `totalboost` | evidence B: OECD20 | yes |
| `training algorithm*` | LIU21 |  |
| `transductive learning` | LIU21 |  |
| `transfer learning` | LIU21 | yes |
| `transformer` | own, from the simplified query | yes |
| `transformer network*` | own, from the simplified query | yes |
| `u-net` | own, added for recall |  |
| `unsupervised learning` | evidence B: Liu+, WIPO19-K1, OECD20, AIW, CSET20 | yes |
| `variational inference` | evidence B: OECD20 | yes |
| `vector machine` | evidence B: OECD20 | yes |
| `virtual assistant*` | OECD20; ATI21 |  |
| `vision transformer` | own, from the simplified query | yes |
| `voice recognition` | ATI21 | yes |
| `wasserstein gan` | own, from the simplified query | yes |
| `word embedding*` | own, added for recall |  |
| `word2vec` | own, from the simplified query | yes |
| `xai` | own, added for recall |  |
| `xgboost` | evidence B: Liu+, WIPO19-K1, OECD20 | yes |
| `xgboost*` | LIU21 |  |
| `yolo*` | own, added for recall |  |
| `zero-shot` | CSET20 |  |

## IOT: Internet of Things

Physical devices and objects that sense or act and are connected to a network, with the services that collect, exchange and process their data.

### Simplified, 22 terms

Terms not in the extended query are marked with a dagger (†).

`connected device*`, `connected home*`, `cyber-physical system*`, `human-machine interface*`, `hyper connectivity`, `industrial internet of things`, `intelligent factor*`, `internet of everything`, `internet of things`, `iot`, `machine-to-enterprise`, `machine-to-human`, `machine-to-machine`, `pervasive sensing`, `sensor network*`, `smart device*`, `smart factor*`, `smart home*`, `smart sensor*`, `wearable*`, `wireless body area network*`, `wireless sensor network*`

### Extended, 92 terms

| term | source | also in simplified |
|---|---|---|
| `aiot` | ZHANGTAO21 |  |
| `ambient assisted living` | own, added for recall |  |
| `ambient intelligence` | EPO20A; UKIPO14IOT; MMM21 |  |
| `arduino` | own, added for recall |  |
| `artificial intelligence of things` | ZHANGTAO21 |  |
| `bluetooth low energy` | own, added for recall |  |
| `body area network*` | own, added for recall |  |
| `car-to-car` | EPO20A |  |
| `cloud of things` | UKIPO14IOT |  |
| `connected car` | ATI21 |  |
| `connected device*` | evidence C: S19 (ATI IoT web keywords "connected devices"; LinkedIn IoT and Connectivity "connected devices"; Dealroom "connected device") | yes |
| `connected home*` | own, from the simplified query | yes |
| `connected object*` | MMM21; ATI21 |  |
| `connected vehicle*` | EPO20A; OECD18IOT |  |
| `cyber-physical` | EPO20A; ATI21 |  |
| `cyber-physical system*` | evidence C: S17 ("(W CYBER+, PHYSI+, SYSTEM+)"), S19 (IoT keywords, LinkedIn IoT), S12 (equivalence with IoT) | yes |
| `d2d communication*` | own, added for recall |  |
| `device-to-device communication*` | EPO20A |  |
| `device-to-device d2d` | own, added for recall |  |
| `esp32` | own, added for recall |  |
| `fitness tracker*` | ATI21 |  |
| `home automation` | EPO20A; ATI21 |  |
| `human-machine interface*` | evidence C: S19 (IoT application area "human machine interface (HMI)") | yes |
| `hyper connectivity` | own, from the simplified query | yes |
| `iiot` | ATI21 |  |
| `industrial internet` | UKIPO14IOT; MMM21 |  |
| `industrial internet of things` | evidence C: S19 (definition and keyword), S18 (Benassi class), S26 ("Industrial Internet" synonym) | yes |
| `intelligent building*` | EPO20A; ATI21 |  |
| `intelligent factor*` | own, from the simplified query | yes |
| `intelligent transport* system*` | ITUY2060; ATI21 |  |
| `inter-vehicle communication*` | EPO20A; MERIT23 |  |
| `internet of energy` | own, added for recall |  |
| `internet of everything` | evidence C: S17, S18, S26 | yes |
| `internet of medical things` | CHIROMA24 |  |
| `internet of things` | evidence C: S1, S2, S17, S18, S19, S21, S22, S32, S33 | yes |
| `internet of underwater things` | own, added for recall |  |
| `internet of vehicles` | evidence C: S19 (under Mobility, not IoT) |  |
| `iomt` | CHIROMA24 |  |
| `iot` | evidence C: S17 ("IOT"), S19 ("IoT"), S21, S22 ("iot"), S33 | yes |
| `lorawan` | ATI21 |  |
| `low power wide area` | ATI21; EPO20 |  |
| `lpwa` | ATI21 |  |
| `lpwan` | EPO20A; ATI21 |  |
| `m2m` | EPO20A; MERIT23; ATI21; OECD18IOT; UKIPO14IOT |  |
| `machine type communication*` | EPO20A; ITUM2083 |  |
| `machine-to-enterprise` | own, from the simplified query | yes |
| `machine-to-human` | own, from the simplified query | yes |
| `machine-to-machine` | evidence C: S17 ("MACHINE_TO_MACHINE", "M2M"), S13, S19, S26, S39 | yes |
| `mmtc` | ITUM2083 |  |
| `mqtt` | own, added for recall |  |
| `near field communication` | ATI21; GUBBI13 |  |
| `networked device*` | MMM21; ATI21 |  |
| `pervasive comput*` | MMM21 |  |
| `pervasive sensing` | own, from the simplified query | yes |
| `predictive maintenance` | ATI21 |  |
| `radio frequency identification` | ATI21; ITUY2060; GUBBI13 |  |
| `raspberry pi` | own, added for recall |  |
| `remote monitoring` | ATI21 |  |
| `rfid` | ATI21; OECD17ICT; GUBBI13; ITUY2060 |  |
| `sensor network*` | evidence C: S17 ("SENSOR_NETWORK"), S18, S23, S38 | yes |
| `sensor node*` | EPO20A; MERIT23; GUBBI13 |  |
| `sigfox` | ATI21; OECD18IOT |  |
| `smart building*` | EPO20A; ATI21 |  |
| `smart device*` | evidence C: S19 ("smart device") | yes |
| `smart dust` | MMM21; ATI21 |  |
| `smart environment*` | GUBBI13 |  |
| `smart factor*` | evidence C: S16 ("Smart factories"), S19 ("smart factory") | yes |
| `smart grid*` | MMM21; ITUY2060 |  |
| `smart health` | EPO20A; ATI21 |  |
| `smart home*` | evidence C: S17 ("(1W SMART, HOME)"), S19, S21, S1 | yes |
| `smart house` | EPO20A |  |
| `smart meter*` | EUROSTAT22IOT; OECD18IOT; UKIPO14IOT; MMM21 |  |
| `smart office` | EPO20A; ATI21 |  |
| `smart sensor*` | evidence C: S39 ("smart sensors") | yes |
| `smart-watch*` | ISO20924 (wearables); OECD18IOT |  |
| `ubiquitous computing` | EPO20A; UKIPO14IOT; MMM21 |  |
| `ubiquitous sensing` | GUBBI13 |  |
| `v2i` | own, added for recall |  |
| `v2v` | EPO20A; ITUM2083 |  |
| `v2x` | EPO20A; MERIT23 |  |
| `vanet*` | own, added for recall |  |
| `vehicle-to-everything` | EPO20A |  |
| `vehicle-to-infrastructure` | EPO20A; ITUM2083 |  |
| `vehicle-to-vehicle` | EPO20A; ITUM2083 |  |
| `vehicular network*` | own, added for recall |  |
| `wearable*` | evidence C: S2 (wearable device), S15, S16, S19 ("smart wearable"; Crunchbase "Wearables"), S21 | yes |
| `web of things` | EPO20A; UKIPO14IOT; MMM21 |  |
| `wireless body area network*` | own, from the simplified query | yes |
| `wireless sensor network*` | evidence C: S17 ("WSN"), S18, S19 (LinkedIn IoT), S38 | yes |
| `wireless sensor*` | EPO20A; GUBBI13 |  |
| `wsn` | EPO20A; MERIT23 |  |
| `zigbee` | own, added for recall |  |

## CI: Computing infrastructure

Shared or specialised computing and network resources: cloud, edge and fog computing, data centres, high-performance and quantum computing, accelerator hardware, big data platforms, and mobile networks such as 5G. Ordinary computers and generic software are not meant.

### Simplified, 53 terms

Terms not in the extended query are marked with a dagger (†).

`5g`, `5g networks`, `5th generation mobile`, `cloud application*`, `cloud architecture*`, `cloud broker`, `cloud client`, `cloud computing`, `cloud infrastructure*`, `cloud migration`, `cloud optimizer`, `cloud platform*`, `cloud portfolio`, `cloud provider`, `cloud server*`, `cloud service*`, `cloud sourcing`, `cloud storage`, `cluster computing`, `cognitive comput*`, `community cloud*`, `cyberinfrastructure*`, `data center*` †, `data centre*` †, `data-intensive comput*`, `decentralized computing`, `dew computing`, `distributed computing`, `dynamic cloud*`, `edge computing`, `federated cloud*`, `fifth generation mobile`, `fog computing`, `grid computing`, `hardware accelerator*`, `high performance comput*`, `hybrid cloud*`, `infrastructure as a service`, `inter-cloud computing`, `massively parallel processing`, `multi-cloud*`, `neuromorphic comput*`, `on-demand computing`, `optical comput*`, `parallel computing`, `photonic comput*`, `platform as a service`, `private cloud*`, `public cloud*`, `quantum comput*`, `real-time comput*`, `software as a service`, `supercomput*`

### Extended, 161 terms

| term | source | also in simplified |
|---|---|---|
| `5g` | EPO20A; MERIT23; ATI21 | yes |
| `5g networks` | evidence C: S21, S22 ("5g network") | yes |
| `5th generation mobile` | evidence C: S15 ("The 5th generation (5G) of mobile networks") | yes |
| `6g` | ITUM2160 |  |
| `6th generation mobile` | own, added for recall |  |
| `amazon web services` | ATWATCH20; MMM21 |  |
| `anything as a service` | ATI21 |  |
| `apache cassandra` | MMM21 | yes |
| `apache hive` | MMM21 | yes |
| `apache kafka` | MMM21 | yes |
| `apache spark` | MMM21 | yes |
| `aws` | MMM21 |  |
| `b5g` | own, added for recall |  |
| `bigtable` | own, from the simplified query | yes |
| `cloud application*` | evidence C: S24 ("cloud app%") | yes |
| `cloud architecture*` | evidence C: S24 ("cloud architectur%") | yes |
| `cloud broker` | own, from the simplified query | yes |
| `cloud client` | own, from the simplified query | yes |
| `cloud computing` | evidence C: S3, S2 (ISO 17788), S16, S17, S19, S20, S24, S25 | yes |
| `cloud environment*` | own, added for recall |  |
| `cloud infrastructure*` | evidence C: S3 (footnote 2), S19 (LinkedIn), S24 | yes |
| `cloud migration` | own, from the simplified query | yes |
| `cloud optimizer` | own, from the simplified query | yes |
| `cloud platform*` | evidence C: S19 ("Google cloud platform", "Sap Cloud platform"), S42 | yes |
| `cloud portfolio` | own, from the simplified query | yes |
| `cloud provider` | evidence C: S13 ("IoT cloud providers"), S2 (term "cloud service provider" in ISO/IEC 20924, from ISO/IEC 17788) | yes |
| `cloud resource*` | evidence C: S3 ("computing resources"), S20 |  |
| `cloud securit*` | MMM21; EPO20A |  |
| `cloud server*` | evidence C: S17 ("(4UG CLOUD, ... SERVER ...)"), S18 | yes |
| `cloud service*` | evidence C: S17, S19, S24, S2 (3.1.8 cloud service) | yes |
| `cloud software` | MMM21; EPO20A |  |
| `cloud solution*` | MMM21; EPO20A |  |
| `cloud sourcing` | own, from the simplified query | yes |
| `cloud storage` | evidence C: S15, S16 ("Intelligent cloud storage"), S17 (Software: "Cloud storage" G06F3/067), S24 | yes |
| `cloud technolog*` | MMM21; EPO20A |  |
| `cloud-based` | MMM21; UKIPO14BD; GORELICK17 |  |
| `cloud-edge` | ATWATCH20 |  |
| `cloud-native` | own, added for recall |  |
| `cloudera` | MMM21 |  |
| `cloudlet*` | NIST500325 |  |
| `cluster comput*` | MMM21; EPO20A |  |
| `cluster computing` | evidence C: S24 ("cluster comput%"), S17 ("(3D CLUSTER+, SERVER?)") | yes |
| `cluster server*` | EPO20A; MERIT23 |  |
| `community cloud*` | evidence C: S3 | yes |
| `computation offloading` | own, added for recall |  |
| `compute-in-memory` | own, added for recall |  |
| `computing continuum` | ATWATCH20 |  |
| `computing-in-memory` | own, added for recall |  |
| `concurrent comput*` | MMM21 |  |
| `cyberinfrastructure*` | own, from the simplified query | yes |
| `data warehous*` | MMM21; ATI21; UKIPO14BD |  |
| `data-center*` | EPO17; EPO20; OECD19 |  |
| `data-centre*` | EPO17; EPO20; OECD19 |  |
| `data-intensive comput*` | own, from the simplified query | yes |
| `decentralized computing` | own, from the simplified query | yes |
| `dew computing` | own, from the simplified query | yes |
| `distributed comput*` | MMM21; EPO20A |  |
| `distributed computing` | evidence C: S5 (3.1.1 definition), S15 ("distributed computing and data storage"), S24, S27 ("distributed process*") | yes |
| `distributed file system*` | own, from the simplified query | yes |
| `docker` | ISOTR23188 | yes |
| `dynamic cloud*` | own, from the simplified query | yes |
| `edge ai` | own, added for recall |  |
| `edge computing` | evidence C: S4, S5, S6, S19 (cloud, IoT and big data lists), S20 | yes |
| `edge device*` | ATWATCH20; NIST500325 |  |
| `edge intelligence` | own, added for recall |  |
| `edge node*` | NIST500325; ISOTR23188 |  |
| `edge server*` | ISOTR23188; NIST500325 |  |
| `edge-cloud` | ATWATCH20 |  |
| `elastic-search` | MMM21 |  |
| `embb` | ITUM2083 |  |
| `exascale` | BIANCHINI26 |  |
| `federated cloud*` | own, from the simplified query | yes |
| `field programmable gate array*` | ATI21; EPO20A |  |
| `fifth generation mobile` | own, from the simplified query | yes |
| `fog computing` | evidence C: S4, S39, S40 | yes |
| `fog node*` | NIST500325 |  |
| `fpga*` | ATI21; EPO20A; ISOTR23188 |  |
| `google cloud` | MMM21; ATI21; ATWATCH20 |  |
| `google earth engine` | GORELICK17; AMANI20; NIST800145 (PaaS) |  |
| `gpu*` | NIST800223; ISOTR23188 |  |
| `graphics processing unit*` | NIST800223; ISOTR23188 |  |
| `grid comput*` | MMM21; EPO20A |  |
| `grid computing` | evidence C: S17 ("(D COMPUT+, GRID?)"), S24, S25 (G06F9/5072 grid computing as cloud), S27 | yes |
| `hadoop` | MMM21; UKIPO14BD; ATI21 | yes |
| `hardware acceleration` | NIST800223 |  |
| `hardware accelerator*` | evidence C: S9 ("hardware accelerators"), S9 intro ("hardware acceleration technology") | yes |
| `hbase` | own, from the simplified query | yes |
| `high performance comput*` | evidence C: S9, S19 (LinkedIn Cloud and Adv. Manufacturing; IoT data infrastructure), S31 | yes |
| `hybrid cloud*` | evidence C: S3, S19, S24 | yes |
| `hypervisor*` | MMM21 |  |
| `imt-2020` | ITUM2083 |  |
| `imt-2030` | ITUM2160 |  |
| `in-memory computing` | SEBASTIAN20 |  |
| `infrastructure as a service` | evidence C: S3, S17, S19 | yes |
| `inter-cloud` | MMM21 |  |
| `inter-cloud computing` | evidence C: S24 ("InterCloud") | yes |
| `kubernetes` | own, added for recall |  |
| `mapreduce` | evidence B: OECD20 | yes |
| `massively parallel processing` | evidence C: S27 ("massively parallel process*"); S31 lists "massive parallel processing" as an AI keyword | yes |
| `memristor*` | own, added for recall |  |
| `microservice*` | ISOTR23188 |  |
| `microsoft azure` | ATWATCH20; MMM21 |  |
| `mist computing` | NIST500325 |  |
| `mobile edge` | ETSIMEC15; ISOTR23188 |  |
| `multi-access edge` | own, added for recall |  |
| `multi-cloud*` | own, from the simplified query | yes |
| `multi-core comput*` | own, added for recall |  |
| `multi-core cpu*` | own, added for recall |  |
| `multi-core processor*` | own, added for recall |  |
| `multitenan*` | MMM21 |  |
| `network slicing` | own, added for recall |  |
| `neuromorphic` | ATI21 |  |
| `neuromorphic comput*` | evidence C: S19 ("neuromorphic computing" new technology; "neuromorphic" micro-electronics) | yes |
| `nosql` | MMM21 |  |
| `on-demand computing` | own, from the simplified query | yes |
| `openstack` | MMM21 |  |
| `optical comput*` | own, from the simplified query | yes |
| `parallel comput*` | MMM21; EPO20A |  |
| `parallel computing` | evidence C: S24 ("parallel comput%") | yes |
| `parallel processing` | MMM21; UKIPO14BD |  |
| `photonic comput*` | evidence C: S19 ("photonic computing" under Photonics) | yes |
| `platform as a service` | evidence C: S3, S17, S19 | yes |
| `private cloud*` | evidence C: S3, S19, S24 | yes |
| `public cloud*` | evidence C: S3, S19, S20, S24 | yes |
| `quantum algorithm*` | CPCG06N10; BORNMANN19 |  |
| `quantum annealer*` | BORNMANN19 |  |
| `quantum annealing` | BORNMANN19 (annealer) |  |
| `quantum bit*` | BORNMANN19 |  |
| `quantum circuit*` | CPCG06N10 |  |
| `quantum comput*` | evidence C: S10 (G06N 10/00), S11, S19, S25, S28, S29 | yes |
| `quantum device*` | BORNMANN19 |  |
| `quantum error correction` | BORNMANN19; CPCG06N10 |  |
| `quantum hardware` | BORNMANN19 |  |
| `quantum processor*` | CPCG06N10 |  |
| `quantum simulat*` | BORNMANN19 |  |
| `quantum software` | BORNMANN19 |  |
| `quantum supremacy` | BORNMANN19 |  |
| `qubit*` | CPCG06N10; BORNMANN19; UKIPO14Q |  |
| `real-time comput*` | evidence C: S19 ("real Time Systems" under Adv. Manufacturing), S5 (real time in edge) | yes |
| `server cluster*` | EPO20A; MERIT23 |  |
| `server farm*` | EPO20A; MERIT23 |  |
| `serverless` | ISOTR23188; ATI21 |  |
| `sixth generation mobile` | own, added for recall |  |
| `software as a service` | evidence C: S3, S17, S19 | yes |
| `software-defined network*` | own, added for recall |  |
| `splunk` | MMM21; UKIPO14BD |  |
| `supercomput*` | evidence C: S9, S31 ("supercomputing", "supercomputer") | yes |
| `system-on-a-chip` | ATI21 |  |
| `system-on-chip` | ATI21 |  |
| `systems-on-a-chip` | own, added for recall |  |
| `systems-on-chip` | own, added for recall |  |
| `task offloading` | own, added for recall |  |
| `tensor processing unit*` | AIW21 |  |
| `tinyml` | own, added for recall |  |
| `urllc` | ITUM2083 |  |
| `utility computing` | MMM21 |  |
| `virtual machine*` | ISOTR23188 |  |
| `virtualisation` | MMM21 |  |
| `virtualization` | EPO17; MMM21 |  |
| `vmware` | MMM21 |  |
| `xaas` | ATI21 |  |

## BL: Blockchain

A ledger shared across a network of computers, in which records are grouped into blocks linked by cryptographic hashes and validated by a consensus mechanism, and the applications built on it, cryptocurrencies included.

### Simplified, 6 terms

Terms not in the extended query are marked with a dagger (†).

`altcoin`, `bitcoin`, `blockchain*`, `cryptocurrenc*`, `private blockchain*`, `public blockchain*`

### Extended, 47 terms

| term | source | also in simplified |
|---|---|---|
| `altcoin` | own, from the simplified query | yes |
| `altcoin*` | own, added for recall |  |
| `bitcoin` | evidence D: B1, B3, B4, B7, X4 | yes |
| `bitcoin*` | NISTIR8202 (plural of a WoS term) |  |
| `block-chain` | own, added for recall |  |
| `blockchain*` | evidence D: B1, B2, B3, B4, B5, X1, X3, X4 | yes |
| `cbdc` | own, added for recall |  |
| `central bank digital currenc*` | own, added for recall |  |
| `consensus algorithm*` | NISTIR8202 |  |
| `consensus mechanism*` | NISTIR8202; ISO22739; OECDBC18 |  |
| `crypto market*` | own, added for recall |  |
| `crypto-asset*` | ISO22739 |  |
| `crypto-currenc*` | BAO25 |  |
| `cryptoasset*` | ISO22739; ATI21 |  |
| `cryptocurrenc*` | evidence D: B1, B2 (3.15), B4, B7, X1, X4 | yes |
| `decentralised application*` | BAO25 |  |
| `decentralised autonomous organisation*` | BAO25 |  |
| `decentralised financ*` | BAO25 |  |
| `decentralised ledger*` | BAO25 |  |
| `decentralized application*` | ISO22739; BAO25 |  |
| `decentralized autonomous organization*` | BAO25 |  |
| `decentralized financ*` | BAO25 |  |
| `decentralized ledger*` | BAO25 |  |
| `digital asset*` | ISO22739; BAO25 |  |
| `digital currenc*` | OECDBC18 |  |
| `distributed ledger*` | ISO22739; NISTIR8202; OECDBC18; BAO25; ATI21 |  |
| `ethereum` | NISTIR8202; BAO25; ATI21 |  |
| `hyperledger` | NISTIR8202; BAO25 |  |
| `initial coin offering*` | own, added for recall |  |
| `layer 2 scaling solution*` | BAO25 |  |
| `non-fungible token*` | BAO25; ISO22739 |  |
| `optimistic rollup*` | BAO25 |  |
| `permissioned` | NISTIR8202; OECDBC18 |  |
| `permissionless` | NISTIR8202; OECDBC18 |  |
| `private blockchain*` | evidence D: B3 | yes |
| `proof of authority` | NISTIR8202 |  |
| `proof-of-stake` | NISTIR8202; BAO25 |  |
| `proof-of-work` | NISTIR8202 |  |
| `public blockchain*` | evidence D: B3 | yes |
| `smart contract*` | NISTIR8202; ISO22739; BAO25; ANTE21 |  |
| `stablecoin*` | own, added for recall |  |
| `tokenomics` | own, added for recall |  |
| `virtual currenc*` | own, added for recall |  |
| `web 3.0` | own, added for recall |  |
| `web3` | own, added for recall |  |
| `zk-rollup*` | BAO25 |  |
| `zk-snark*` | BAO25 |  |

## ROB: Robotics

Programmed physical machines that sense and act on their environment with a degree of autonomy, to move, manipulate or position: industrial, service, medical and mobile robots, drones and other unmanned or self-driving vehicles.

### Simplified, 25 terms

Terms not in the extended query are marked with a dagger (†).

`autonomous car*`, `autonomous underwater vehicle*`, `autonomous vehicle*`, `auv`, `chatbot*` †, `cybernetics`, `drone*`, `humanoid robot*`, `manipulator*`, `mobile manipulator*`, `mobile robot*`, `robot*`, `robotic*`, `self-driving car*`, `self-driving vehicle*`, `uav`, `ugv`, `uncrewed vehicle*`, `unmanned aerial vehicle*`, `unmanned air vehicle*`, `unmanned aircraft system*`, `unmanned ground vehicle*`, `unmanned spacecraft`, `unmanned underwater vehicles*`, `unmanned vehicle*`

### Extended, 79 terms

| term | source | also in simplified |
|---|---|---|
| `aerial vehicle*` | UNCTAD21; WIPOWP30 (inside unmanned aerial vehicle) |  |
| `agv` | ISO8373; MEINDL21 |  |
| `automated car` | MMM21 |  |
| `automated driving` | SAEJ3016 |  |
| `automated guided vehicle*` | ISO8373; IFR25; MEINDL21 |  |
| `automated vehicle*` | SAEJ3016; UKIPORAS14 |  |
| `autonomous aerial system*` | HLADCHENKO26 |  |
| `autonomous aircraft` | ICAO328 |  |
| `autonomous car*` | own, from the simplified query | yes |
| `autonomous driving` | EPO17; EPO20; ATI21 |  |
| `autonomous flight` | own, added for recall |  |
| `autonomous mobile` | IFR25 |  |
| `autonomous navigation` | IFR25 |  |
| `autonomous ship*` | own, added for recall |  |
| `autonomous surface` | IFR25 |  |
| `autonomous underwater vehicle*` | evidence D: R2 (diving robots, class B2), R6 (underwater vehicles) | yes |
| `autonomous vehicle*` | evidence D: R5, R6, R7, R9, X1, X3 (Vehicles domain), X4 (IT for Mobility), X6 | yes |
| `autonomous vessel*` | own, added for recall |  |
| `auv` | own, from the simplified query | yes |
| `cobot*` | ATI21; MMM21 |  |
| `collision avoidance` | OECD20 |  |
| `cybernetics` | own, from the simplified query | yes |
| `driverless` | SAEJ3016; MMM21 |  |
| `driving automation` | SAEJ3016 |  |
| `drone*` | evidence D: R5, R6, R8, R9, X1 (own technology), X4 (robotics) | yes |
| `end effector*` | own, added for recall |  |
| `exoskeleton*` | ISO8373; IFR25; WIPOWP30; ATI21; WEN24 |  |
| `hexacopter*` | own, added for recall |  |
| `humanoid robot*` | evidence D: R5, X1 ("humanoids") | yes |
| `low altitude platform*` | HLADCHENKO26 |  |
| `manipulator*` | evidence D: R1 (§ 3.6 head noun), R5 (B25J classes) | yes |
| `microrobot*` | own, added for recall |  |
| `mobile manipulator*` | own, from the simplified query | yes |
| `mobile robot*` | evidence D: R1 (§ 4.15), R2 | yes |
| `motion planning` | OECD20 |  |
| `multi-rotor*` | HLADCHENKO26 |  |
| `multicopter*` | own, added for recall |  |
| `nanorobot*` | own, added for recall |  |
| `obstacle avoidance` | OECD20 |  |
| `quad-rotor*` | HLADCHENKO26 |  |
| `quadcopter*` | HLADCHENKO26 (quadrotor) |  |
| `remotely operated underwater vehicle*` | own, added for recall |  |
| `remotely operated vehicle*` | ISO8373 (6.17) |  |
| `remotely piloted aircraft*` | ICAO328 |  |
| `robo-taxi*` | own, added for recall |  |
| `robot*` | evidence D: R1, R2, R5 (patent terms), R9, X1, X4, X5 | yes |
| `robotic*` | evidence D: R5 ("robotic"), X4, X1 ("robotics") | yes |
| `rpas` | ICAO328; HLADCHENKO26 |  |
| `self-driving` | SAEJ3016; IFR25 |  |
| `self-driving car*` | evidence D: R2 ("self-driving cars and buses", excluded), R6, R9 (tested) | yes |
| `self-driving vehicle*` | evidence D: R2 | yes |
| `simultaneous localisation and mapping` | own, added for recall |  |
| `simultaneous localization and mapping` | OECD20 |  |
| `tele-operat*` | ISO8373; WIPOWP30 |  |
| `telerobot*` | own, added for recall |  |
| `trajectory planning` | OECD20 |  |
| `trajectory tracking` | OECD20 |  |
| `uas` | ICAO328; UNCTAD21; WIPOWP30; HLADCHENKO26 |  |
| `uav` | evidence D: R5, R8, R9, X1 | yes |
| `uav*` | UNCTAD21; WIPOWP30; HLADCHENKO26; LIANG23 |  |
| `ugv` | evidence D: R9 (tested, excluded as redundant) | yes |
| `ugv*` | LIANG23 |  |
| `uncrewed` | own, added for recall |  |
| `uncrewed aerial*` | own, added for recall |  |
| `uncrewed vehicle*` | own, from the simplified query | yes |
| `unmanned` | WIPOWP30; ICAO328 |  |
| `unmanned aerial system*` | WIPOWP30 |  |
| `unmanned aerial vehicle*` | evidence D: R5, R6, X1 | yes |
| `unmanned air vehicle*` | own, from the simplified query | yes |
| `unmanned aircraft system*` | evidence D: R4 (ICAO), X1 ("unmanned aircraft systems") | yes |
| `unmanned ground vehicle*` | evidence D: R9 (tested, added no records), R5 ("unmanned [...] land vehicles") | yes |
| `unmanned spacecraft` | evidence D: R2 (class E1 "robots for orbital space") | yes |
| `unmanned surface ve*` | IFR25 (class B1) |  |
| `unmanned underwater vehicle*` | UKIPORAS14 (singular of a WoS term) |  |
| `unmanned underwater vehicles*` | evidence D: R6, R9 ("UUV") | yes |
| `unmanned vehicle*` | own, from the simplified query | yes |
| `unoccupied aerial*` | own, added for recall |  |
| `uuv*` | LIANG23 |  |
| `visual servoing` | OECD20 |  |

## AM: Additive manufacturing

Computer-controlled production that creates three-dimensional objects by joining materials layer by layer, 3D printing included.

### Simplified, 29 terms

Terms not in the extended query are marked with a dagger (†).

`3d print*`, `3d prototyping`, `additive fabrication`, `additive layer manufacturing`, `additive manufacturing`, `binder jetting`, `composite filament fabrication`, `continuous liquid interface production`, `direct digital manufacturing`, `direct ink writing`, `direct metal laser sintering`, `directed energy deposition`, `electron-beam freeform fabrication`, `electron-beam melting`, `fused deposition modeling`, `fused filament fabrication`, `industry 4.0`, `laminated object manufacturing`, `layered manufacturing`, `material extrusion`, `material jetting`, `powder bed fusion`, `rapid prototyping`, `robocasting`, `selective laser melting`, `selective laser sintering`, `sheet lamination`, `stereolithography`, `vat photopolymerization`

### Extended, 85 terms

| term | source | also in simplified |
|---|---|---|
| `3-d print*` | UKIPO13; LEZAMA18; ATI21 |  |
| `3-dimensional print*` | LEZAMA18 |  |
| `3d bioprint*` | CELIK26; XUE23 |  |
| `3d concrete print*` | HE22 |  |
| `3d fabrication` | UKIPO13; MMM21 |  |
| `3d food print*` | EPO23AM; XUE23 |  |
| `3d manufacturing` | UKIPO13; MMM21 |  |
| `3d print*` | evidence D: A1 (3.3.1), A2, A3, A4, A5, A7, X1, X2, X3, X4 ("3-D Printing") | yes |
| `3d prototyping` | own, from the simplified query | yes |
| `3dp` | EPO17 |  |
| `4d print*` | EPO17 |  |
| `additive fabrication` | evidence D: A1 (historical term), A2 | yes |
| `additive layer manufacturing` | evidence D: A1 (historical term) | yes |
| `additive manufactur*` | UKIPO13; LEZAMA18 |  |
| `additive manufacturing` | evidence D: A1, A2, A3, A4, A5, X1, X2, X4 | yes |
| `additively manufactur*` | UKIPO13 (additive NEAR manufactur*) |  |
| `binder jet*` | LEZAMA18 |  |
| `binder jetting` | evidence D: A1, A3, X2 | yes |
| `bio-print*` | XUE23 |  |
| `bioprint*` | EPO17; EPO23AM; CELIK26 |  |
| `composite filament fabrication` | own, from the simplified query | yes |
| `continuous liquid interface production` | own, from the simplified query | yes |
| `digital light processing` | own, added for recall |  |
| `direct digital manufacturing` | evidence D: A8 (title) | yes |
| `direct energy deposition` | LEZAMA18 |  |
| `direct ink writing` | own, from the simplified query | yes |
| `direct metal deposition` | LEZAMA18 |  |
| `direct metal laser sintering` | evidence D: A3 | yes |
| `directed energy deposition` | evidence D: A1, A3 ("Direct* energy deposition") | yes |
| `directed light fabrication` | LEZAMA18 |  |
| `electron-beam freeform fabrication` | evidence D: A2 ("EBF3") | yes |
| `electron-beam melt*` | LEZAMA18 |  |
| `electron-beam melting` | evidence D: A3 ("Electron beam" NEAR/1 "Melt*") | yes |
| `free-form fabrication` | UKIPO13 |  |
| `freeform fabrication` | ISOASTM52900; UKIPO13 |  |
| `fused deposition modeling` | evidence D: A2 ("fuse deposition model"), A3, X2, X5 | yes |
| `fused deposition modelling` | UKIPO13 |  |
| `fused filament fabrication` | evidence D: A3 | yes |
| `fused layer modeling` | LEZAMA18 |  |
| `fused layer modelling` | own, added for recall |  |
| `generative printing` | UKIPO13 |  |
| `inkjet print*` | LEZAMA18 (only with AM context) |  |
| `laminat* object manufactur*` | UKIPO13; LEZAMA18 |  |
| `laminated object manufacturing` | evidence D: A2 ("laminate object manufacturing"), A3 ("Lamination object manufactur*") | yes |
| `laser cladding` | LEZAMA18 |  |
| `laser consolidation` | LEZAMA18 |  |
| `laser direct casting` | LEZAMA18 |  |
| `laser engineered net shaping` | LEZAMA18 |  |
| `laser freeform fabrication` | LEZAMA18 |  |
| `laser metal deposition` | LEZAMA18; EPO17 |  |
| `laser-based metal deposition` | LEZAMA18 |  |
| `layer manufacturing` | ISOASTM52900 |  |
| `layered manufacturing` | evidence D: A5 ("Layered Manufacturing"); A1 has "layer manufacturing" | yes |
| `material extrusion` | evidence D: A1, A3 | yes |
| `material jet*` | LEZAMA18 |  |
| `material jetting` | evidence D: A1, A3 | yes |
| `multi-jet modeling` | LEZAMA18 |  |
| `multi-jet modelling` | own, added for recall |  |
| `plastic jet printing` | LEZAMA18 |  |
| `powder bed fusion` | evidence D: A1, A3 | yes |
| `rapid manufactur*` | UKIPO13; CELIK26 |  |
| `rapid prototyping` | evidence D: A2, A5, A8 (title), X4 (under Advanced Manufacturing), X5 | yes |
| `rapid tooling` | CELIK26 |  |
| `robocasting` | own, from the simplified query | yes |
| `selective heat sintering` | UKIPO13 |  |
| `selective laser deposition` | MMM21 |  |
| `selective laser manufactur*` | MMM21 |  |
| `selective laser melt*` | LEZAMA18 |  |
| `selective laser melting` | evidence D: A3, X2 | yes |
| `selective laser sinter*` | UKIPO13; LEZAMA18 |  |
| `selective laser sintering` | evidence D: A2, A3, X2, X5 | yes |
| `sheet lamination` | evidence D: A1, A3 | yes |
| `stereolithograph*` | LEZAMA18 |  |
| `stereolithography` | evidence D: A2, A3, X2, X5 | yes |
| `thermojet` | LEZAMA18 |  |
| `thin-film photopolymerisation` | own, added for recall |  |
| `thin-film photopolymerization` | LEZAMA18 |  |
| `three-d print*` | LEZAMA18 |  |
| `three-dimensional print*` | UKIPO13; LEZAMA18 |  |
| `two-photon polymerisation` | own, added for recall |  |
| `two-photon polymerization` | own, added for recall |  |
| `ultrasonic consolidation` | LEZAMA18 |  |
| `vat photopolymerisation` | EPO23AM |  |
| `vat photopolymerization` | evidence D: A1 (3.2.7), A3, A4 | yes |
| `voxeljet` | LEZAMA18 |  |

## UMBRELLA: Umbrella terms

General terms for digital technologies as a whole or for their combination, such as digital transformation, Industry 4.0 or smart cities, that name no single group. Extended query only.

### Extended, 26 terms

| term | source | also in simplified |
|---|---|---|
| `4ir` | EPO17 |  |
| `4th industrial revolution` | own, added for recall |  |
| `cloud manufacturing` | MEINDL21 |  |
| `digital manufacturing` | MEINDL21 |  |
| `digital technolog*` | own, added for recall |  |
| `digital transformation` | EUDD22 (a process) |  |
| `digital twin*` | EPO20; MMM21 |  |
| `digitalisation` | EUDD22 (a process) |  |
| `digitalization` | EUDD22 (a process) |  |
| `factories of the future` | MEINDL21 |  |
| `factory of the future` | MEINDL21 |  |
| `fourth industrial revolution` | EPO17; OECD17; MMM21 |  |
| `i4.0` | own, added for recall |  |
| `industrial revolution 4.0` | own, added for recall |  |
| `industrie 4.0` | MEINDL21; KAGERMANN13 |  |
| `industry 4.0` | EPO17; ATI21; OECD17; UNCTAD21; MMM21; MEINDL21 | yes |
| `industry 5.0` | own, added for recall |  |
| `industry4.0` | own, added for recall |  |
| `intelligent city` | EPO20A |  |
| `intelligent manufacturing` | MEINDL21 |  |
| `precision agriculture` | EPO20 |  |
| `smart agricultur*` | EPO20 |  |
| `smart cit*` | UNCTAD21; EPO20A; ATI21 |  |
| `smart farming` | EPO20; UNCTAD21 |  |
| `smart manufacturing` | MEINDL21; ATI21 |  |
| `society 5.0` | own, added for recall |  |
