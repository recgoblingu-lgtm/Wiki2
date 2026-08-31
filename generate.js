const fs = require("fs");
const fetch = require("node-fetch");

async function getRandomArticle() {
  const res = await fetch("https://en.wikipedia.org/api/rest_v1/page/random/summary");
  const data = await res.json();

  return {
    title: data.title,
    summary: data.extract,
    image: data.thumbnail ? data.thumbnail.source : null
  };
}

function createHTML(title, summary, image) {
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>${title} - Wiki2</title>
<link href="../style.css" rel="stylesheet"/>
</head>
<body>
<div class="container">

<div class="sidebar">
<h2>Wiki2</h2>
<a href="../index.html">Main Page</a>
</div>

<div class="content">

<h1>${title}</h1>

${image ? `
<figure class="article-image">
<img src="${image}" alt="${title}">
<figcaption>${title}</figcaption>
</figure>
` : ""}

<p>${summary}</p>

<hr/>
<p><i>Auto-generated from Wikipedia</i></p>

</div>
</div>
</body>
</html>`;
}

async function run() {
  const used = new Set();

  for (let i = 0; i < 20; i++) {
    const article = await getRandomArticle();

    // avoid duplicates in same run
    if (used.has(article.title)) continue;
    used.add(article.title);

    const safeName = article.title
      .replace(/[^\w\s]/gi, "")
      .replace(/\s+/g, "_");

    const fileName = `${safeName}.html`;

    fs.writeFileSync(
      `articles/${fileName}`,
      createHTML(article.title, article.summary, article.image)
    );

    console.log("Created:", fileName);
  }
}

run();