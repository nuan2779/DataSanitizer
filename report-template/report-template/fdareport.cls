% fdareport.cls — Report template, Faculty of Data Science and Artificial Intelligence (FDA), NEU
% Compile with XeLaTeX (or LuaLaTeX):  latexmk -xelatex main.tex
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{fdareport}[2026/10/31 FDA group report class]
\LoadClass[13pt,a4paper]{extarticle}

%---------------------------------------------------------------- packages
\RequirePackage{fontspec}
\RequirePackage[a4paper,top=2.5cm,bottom=2.5cm,left=3cm,right=2cm,headheight=15pt]{geometry}
\RequirePackage{xcolor}
\RequirePackage{graphicx}
\RequirePackage{tikz}
\RequirePackage{fancyhdr}
\RequirePackage{titlesec}
\RequirePackage{titletoc}
\RequirePackage{setspace}
\RequirePackage{booktabs}
\RequirePackage{tabularx}
\RequirePackage{array}
\RequirePackage{caption}
\RequirePackage{enumitem}
\RequirePackage{listings}
\RequirePackage{tcolorbox}
\RequirePackage{microtype}
\RequirePackage{lastpage}
\RequirePackage{colortbl}
\RequirePackage{url}
\RequirePackage[hidelinks]{hyperref}

%---------------------------------------------------------------- fonts
% TeX Gyre fonts ship with TeX Live / Overleaf, so no system font is needed.
% They also cover Vietnamese diacritics (for names).
\setmainfont{texgyretermes}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic]
\setsansfont{texgyreheros}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic]
\setmonofont{texgyrecursor}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic,Scale=0.9]
\setstretch{1.3}
\setlength{\parskip}{4pt}
\setlength{\parindent}{1.0cm}

%---------------------------------------------------------------- FDA brand colours
% Blues only, taken from the FDA logo; navy matches the FDA slide theme.
\definecolor{PrussianBlue}{rgb}{0.0,0.19,0.33}     % primary
\definecolor{FDABlue}{rgb}{0,0.376,0.69}            % accent (FDA logo blue)
\definecolor{FDASky}{rgb}{0,0.502,0.722}           % secondary accent (FDA logo light blue)
\definecolor{Astronaut}{rgb}{0.243,0.318,0.416}    % secondary text
\definecolor{Solitude}{rgb}{0.953,0.965,0.976}     % light background
\definecolor{PaleBlue}{rgb}{0.902,0.941,0.98}
\definecolor{PaleSky}{rgb}{0.929,0.965,0.984}

\hypersetup{colorlinks=true,linkcolor=PrussianBlue,urlcolor=FDABlue,citecolor=FDABlue}

%---------------------------------------------------------------- metadata macros
\newcommand{\reporttitle}[1]{\gdef\@reporttitle{#1}}
\newcommand{\reportsubtitle}[1]{\gdef\@reportsubtitle{#1}}
\newcommand{\course}[1]{\gdef\@course{#1}}
\newcommand{\coursecode}[1]{\gdef\@coursecode{#1}}
\newcommand{\semester}[1]{\gdef\@semester{#1}}
\newcommand{\groupname}[1]{\gdef\@groupname{#1}}
\newcommand{\classname}[1]{\gdef\@classname{#1}}
\newcommand{\instructor}[1]{\gdef\@instructor{#1}}
\newcommand{\repourl}[1]{\gdef\@repourl{#1}}
\newcommand{\demourl}[1]{\gdef\@demourl{#1}}
\newcommand{\reportdate}[1]{\gdef\@reportdate{#1}}
% members: rows "No. & Full name & Student ID & Role \\"
\newcommand{\members}[1]{\gdef\@members{#1}}

\reporttitle{}\reportsubtitle{}\course{}\coursecode{}\semester{}\groupname{}
\classname{}\instructor{}\repourl{}\demourl{}\reportdate{\today}\members{}

%---------------------------------------------------------------- headings
\titleformat{\section}
  {\sffamily\bfseries\Large\color{PrussianBlue}}
  {\thesection.}{0.6em}{}
  [{\color{FDABlue}\titlerule[1.2pt]}]
\titleformat{\subsection}
  {\sffamily\bfseries\large\color{PrussianBlue}}{\thesubsection.}{0.6em}{}
\titleformat{\subsubsection}
  {\sffamily\bfseries\normalsize\color{Astronaut}}{\thesubsubsection.}{0.6em}{}
\titlespacing*{\section}{0pt}{18pt}{8pt}
\titlespacing*{\subsection}{0pt}{12pt}{4pt}
\titlespacing*{\subsubsection}{0pt}{8pt}{2pt}

\captionsetup{font={small,sf},labelfont={bf,color=PrussianBlue},labelsep=period}
\setlist{itemsep=2pt,topsep=3pt}

% Table of contents styling
\titlecontents{section}[0em]{\sffamily\bfseries\addvspace{4pt}}
  {\color{PrussianBlue}\contentslabel{1.6em}}{\hspace*{-1.6em}}{\titlerule*[0.6pc]{.}\contentspage}
\titlecontents{subsection}[1.6em]{\sffamily}
  {\contentslabel{2.4em}}{\hspace*{-2.4em}}{\titlerule*[0.6pc]{.}\contentspage}

%---------------------------------------------------------------- header / footer
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\fancyhead[L]{\sffamily\footnotesize\color{Astronaut}\raisebox{-0.2cm}{\includegraphics[height=0.7cm]{logos/FDA_Logo.png}}\hspace{0.4em}Faculty of Data Science and Artificial Intelligence}
\fancyhead[R]{\sffamily\footnotesize\color{Astronaut}\@course\ --- \@groupname}
\fancyfoot[L]{\sffamily\footnotesize\color{Astronaut}National Economics University}
\fancyfoot[R]{\sffamily\footnotesize\color{PrussianBlue}\thepage\,/\,\pageref{LastPage}}
\fancypagestyle{plain}{\fancyhf{}\renewcommand{\headrulewidth}{0pt}
  \fancyfoot[R]{\sffamily\footnotesize\color{PrussianBlue}\thepage\,/\,\pageref{LastPage}}}

% English captions
\renewcommand{\contentsname}{Table of Contents}
\renewcommand{\figurename}{Figure}
\renewcommand{\tablename}{Table}
\renewcommand{\refname}{References}
\renewcommand{\listfigurename}{List of Figures}
\renewcommand{\listtablename}{List of Tables}
\renewcommand{\appendixname}{Appendix}

%---------------------------------------------------------------- code listings
\lstdefinestyle{fda}{
  backgroundcolor=\color{Solitude},
  basicstyle=\ttfamily\footnotesize,
  keywordstyle=\color{FDABlue}\bfseries,
  commentstyle=\color{Astronaut}\itshape,
  stringstyle=\color{FDASky},
  numberstyle=\tiny\color{Astronaut},
  numbers=left,numbersep=6pt,
  frame=leftline,rulecolor=\color{PrussianBlue},
  breaklines=true,keepspaces=true,showstringspaces=false,tabsize=2,
  aboveskip=0.6em,belowskip=0.4em,
  inputencoding=utf8,extendedchars=true
}
\lstdefinelanguage{JavaScript}{
  keywords={const,let,var,function,return,if,else,for,while,async,await,new,class,import,from,export,default,try,catch,throw,true,false,null,undefined},
  morecomment=[l]{//},morecomment=[s]{/*}{*/},morestring=[b]',morestring=[b]",morestring=[b]`,sensitive=true}
\lstdefinelanguage{CSS}{
  morekeywords={@media,@import,@font-face},
  morecomment=[s]{/*}{*/},morestring=[b]',morestring=[b]",sensitive=true}
\lstset{style=fda}

%---------------------------------------------------------------- callout boxes
\tcbuselibrary{skins,breakable}
\newtcolorbox{note}[1][Note]{enhanced,breakable,colback=PaleBlue,colframe=FDABlue,
  fonttitle=\sffamily\bfseries,title=#1,boxrule=0.6pt,arc=2pt,left=6pt,right=6pt,top=4pt,bottom=4pt}
\newtcolorbox{warning}[1][Warning]{enhanced,breakable,colback=PaleSky,colframe=FDASky,
  fonttitle=\sffamily\bfseries,title=#1,boxrule=0.6pt,arc=2pt,left=6pt,right=6pt,top=4pt,bottom=4pt}
% Writing guidance in the template — delete before submitting.
\newcommand{\guide}[1]{\begin{note}[Guidance --- delete before submitting]\small #1\end{note}}

%---------------------------------------------------------------- cover page
\renewcommand{\maketitle}{%
  \begin{titlepage}
  \thispagestyle{empty}
  \newgeometry{top=1.5cm,bottom=2cm,left=2.5cm,right=2cm}
  \setstretch{1.15}\centering\sffamily
  % banner
  \begin{tikzpicture}[remember picture,overlay]
    \fill[Solitude] (current page.north west) rectangle ([yshift=-4.1cm]current page.north east);
    \node[anchor=north west,inner sep=0] at ([xshift=2.5cm,yshift=-0.5cm]current page.north west)
      {\includegraphics[height=3.1cm]{logos/NEU_Logo.png}};
    \node[anchor=north east,inner sep=0] at ([xshift=-2cm,yshift=-0.3cm]current page.north east)
      {\includegraphics[height=3.5cm]{logos/FDA_Logo.png}};
    \node[text=PrussianBlue,align=center,font=\sffamily\bfseries,text width=8cm] at ([yshift=-2.05cm]current page.north)
      {\large NATIONAL ECONOMICS\\UNIVERSITY\\[4pt]
       \small FACULTY OF DATA SCIENCE\\AND ARTIFICIAL INTELLIGENCE};
    \fill[PrussianBlue] ([yshift=-4.1cm]current page.north west) rectangle ([yshift=-4.3cm]current page.north east);
    \fill[FDABlue] ([yshift=-4.3cm]current page.north west) rectangle ([yshift=-4.4cm]current page.north east);
  \end{tikzpicture}
  \vspace*{3.8cm}

  {\color{PrussianBlue}\fontsize{30}{36}\selectfont\bfseries GROUP ASSIGNMENT REPORT\par}
  \vspace{0.3cm}
  {\color{Astronaut}\large Midterm\par}
  \vspace{0.4cm}
  {\color{FDABlue}\Large\bfseries\@course\ (\@coursecode)\par}
  \vspace{1.2cm}
  {\color{PrussianBlue}\fontsize{20}{26}\selectfont\bfseries\@reporttitle\par}
  \ifx\@reportsubtitle\@empty\else
    \vspace{0.4cm}{\color{Astronaut}\Large\@reportsubtitle\par}
  \fi
  \vspace{0.5cm}
  {\color{FDABlue}\rule{3cm}{2pt}\par}
  \vspace{1.2cm}

  \renewcommand{\arraystretch}{1.3}
  \begin{tabular}{@{}r@{\hspace{0.8em}}l@{}}
    \textbf{\color{PrussianBlue}Group:}            & \@groupname \\
    \textbf{\color{PrussianBlue}Class:}    & \@classname \\
    \textbf{\color{PrussianBlue}Instructor:}      & \@instructor \\
    \textbf{\color{PrussianBlue}Semester:}          & \@semester \\
    \ifx\@repourl\@empty\else \textbf{\color{PrussianBlue}GitHub:} & \url{\@repourl} \\ \fi
    \ifx\@demourl\@empty\else \textbf{\color{PrussianBlue}Demo:}   & \url{\@demourl} \\ \fi
  \end{tabular}

  \vspace{0.9cm}
  {\color{PrussianBlue}\bfseries Team Members\par}\vspace{4pt}
  \renewcommand{\arraystretch}{1.25}
  \footnotesize\setlength{\tabcolsep}{5pt}
  \begin{tabular}{@{}clll@{}}
    \toprule
    \rowcolor{Solitude}
    \textbf{No.} & \textbf{Full name} & \textbf{Student ID} & \textbf{Role}\\
    \midrule
    \@members
    \bottomrule
  \end{tabular}

  \vfill
  {\color{Astronaut}\normalsize Hanoi, \@reportdate\par}
  \restoregeometry
  \end{titlepage}
  \setcounter{page}{1}
}
