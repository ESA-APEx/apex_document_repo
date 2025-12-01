import React from "react";
import {
  FaFilePdf,
  FaFileWord,
  FaFileExcel,
  FaFilePowerpoint,
  FaFileAlt,
  FaFileArchive,
} from "react-icons/fa";

type Props = {
  filename?: string | null;
  className?: string;
  size?: number | string;
};

export default function FileIcon({
  filename,
  className = "",
  size = 16,
}: Props) {
  const ext = (filename || "").toString().split(".").pop()?.toLowerCase() || "";

  switch (ext) {
    case "pdf":
      return <FaFilePdf className={className} size={size} />;
    case "doc":
    case "docx":
      return <FaFileWord className={className} size={size} />;
    case "xls":
    case "xlsx":
      return <FaFileExcel className={className} size={size} />;
    case "ppt":
    case "pptx":
      return <FaFilePowerpoint className={className} size={size} />;
    case "zip":
    case "tgz":
    case "tar":
    case "gz":
      return <FaFileArchive className={className} size={size} />;
    default:
      return <FaFileAlt className={className} size={size} />;
  }
}
