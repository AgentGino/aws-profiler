from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="aws-profiler",
    version="1.0.0",
    author="AgentGino",
    author_email="himakar@qwik.tools",
    description="A CLI tool to list AWS profiles and check their credential status",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AgentGino/aws-profiler",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "boto3>=1.26.0",
        "tabulate>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "aws-profiler=aws_profiler.cli:main",
        ],
    },
)
