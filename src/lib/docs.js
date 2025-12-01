import fs from "fs";
import path from "path";
import yaml from "js-yaml";

const PUBLIC_DOCS = "./public/docs";

function readYAML(filePath) {
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    return yaml.load(raw) || {};
  } catch (e) {
    return {};
  }
}

export function getAllDocs() {
  const projects = [];
  if (!fs.existsSync(PUBLIC_DOCS)) return [];
  const projectNames = fs
    .readdirSync(PUBLIC_DOCS, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);

  for (const project of projectNames) {
    const projectDir = path.join(PUBLIC_DOCS, project);
    const files = fs
      .readdirSync(projectDir, { withFileTypes: true })
      .filter(
        (f) =>
          f.isFile() && (f.name.endsWith(".yml") || f.name.endsWith(".yaml"))
      )
      .map((f) => f.name);

    for (const propFile of files) {
      const fullPath = path.join(projectDir, propFile);
      const meta = readYAML(fullPath) || {};
      const slug = propFile.replace(/\.(yml|yaml)$/i, "");
      const filename =
        propFile.replace(/\.(yml|yaml)$/i, "") + "." + meta.format;
      projects.push({
        project,
        filename,
        slug,
        meta,
        url: `/docs/${project}/${filename}`,
      });
    }
  }

  // sort by date if present
  projects.sort((a, b) => {
    const da = a.meta.date ? new Date(a.meta.date) : new Date(0);
    const db = b.meta.date ? new Date(b.meta.date) : new Date(0);
    return db - da;
  });

  return [...projects];
}

export default getAllDocs();
