const DEFAULT_TITLE = "MockMitra";

function upsertMeta(selector, attributes) {
  let element = document.head.querySelector(selector);
  if (!element) {
    element = document.createElement("meta");
    Object.entries(attributes).forEach(([key, value]) => {
      if (key !== "content") {
        element.setAttribute(key, value);
      }
    });
    document.head.appendChild(element);
  }

  if (attributes.content) {
    element.setAttribute("content", attributes.content);
  }
}

function upsertCanonical(url) {
  let canonical = document.head.querySelector("link[rel='canonical']");
  if (!canonical) {
    canonical = document.createElement("link");
    canonical.setAttribute("rel", "canonical");
    document.head.appendChild(canonical);
  }
  canonical.setAttribute("href", url);
}

export function setPageSeo({ title, description, path = "/" }) {
  const pageTitle = title ? `${title} | ${DEFAULT_TITLE}` : DEFAULT_TITLE;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const canonicalUrl = `https://mockmitra.app${normalizedPath}`;

  document.title = pageTitle;

  upsertMeta("meta[name='description']", {
    name: "description",
    content: description,
  });
  upsertMeta("meta[property='og:title']", {
    property: "og:title",
    content: pageTitle,
  });
  upsertMeta("meta[property='og:description']", {
    property: "og:description",
    content: description,
  });
  upsertMeta("meta[property='og:url']", {
    property: "og:url",
    content: canonicalUrl,
  });
  upsertMeta("meta[property='og:image']", {
    property: "og:image",
    content: "https://mockmitra.app/favicon.svg",
  });
  upsertMeta("meta[name='twitter:title']", {
    name: "twitter:title",
    content: pageTitle,
  });
  upsertMeta("meta[name='twitter:description']", {
    name: "twitter:description",
    content: description,
  });
  upsertMeta("meta[name='twitter:image']", {
    name: "twitter:image",
    content: "https://mockmitra.app/favicon.svg",
  });

  upsertCanonical(canonicalUrl);
}
