from __future__ import annotations

from pathlib import Path
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from backend.agent.models import AgentArtifact

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = (ROOT / 'data' / 'outputs').resolve()


def is_reference(value: Any) -> bool:
	return isinstance(value, str) and value.startswith('$') and '.' in value


def download_url_for(filename: str) -> str:
	return f'/api/files/{Path(filename).name}'


def relative_output_path(path: str | Path) -> str:
	resolved = Path(path).resolve()
	try:
		return resolved.relative_to(ROOT).as_posix()
	except ValueError:
		return resolved.name


def artifact_from_output(path: str | Path, artifact_type: str) -> AgentArtifact:
	filename = Path(path).name
	return AgentArtifact(
		filename=filename,
		type=artifact_type,
		path=relative_output_path(path),
		download_url=download_url_for(filename),
	)


def _sample_value(annotation: Any) -> Any:
	origin = get_origin(annotation)
	args = get_args(annotation)
	if origin is list:
		return []
	if origin is dict:
		return {}
	if origin is tuple:
		return ()
	if origin is set:
		return set()
	if origin is None and args:
		return _sample_value(args[0])
	if annotation in {str, Any}:
		return ''
	if annotation is int:
		return 0
	if annotation is float:
		return 0.0
	if annotation is bool:
		return False
	if isinstance(annotation, type) and issubclass(annotation, BaseModel):
		return annotation.model_construct().model_dump()
	return None


def replace_references(value: Any, annotation: Any) -> Any:
	if is_reference(value):
		return _sample_value(annotation)
	origin = get_origin(annotation)
	args = get_args(annotation)
	if isinstance(value, dict):
		if isinstance(annotation, type) and issubclass(annotation, BaseModel):
			field_values: dict[str, Any] = {}
			for field_name, field in annotation.model_fields.items():
				if field_name in value:
					field_values[field_name] = replace_references(value[field_name], field.annotation)
			for key, item in value.items():
				if key not in field_values:
					field_values[key] = replace_references(item, Any)
			return field_values
		if origin is dict and args:
			key_annotation = args[0]
			value_annotation = args[1] if len(args) > 1 else Any
			return {
				replace_references(key, key_annotation): replace_references(item, value_annotation)
				for key, item in value.items()
			}
		return {key: replace_references(item, Any) for key, item in value.items()}
	if isinstance(value, list):
		item_annotation = args[0] if origin is list and args else Any
		return [replace_references(item, item_annotation) for item in value]
	return value
